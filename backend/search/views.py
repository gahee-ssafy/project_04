import json
import time
import asyncio
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import SearchQuery, SearchSource
from .serializers import SearchQuerySerializer, SearchRequestSerializer
from search_engine import run_rag_pipeline, generate_image_answer_stream


# =============================================================
# POST /api/search - 텍스트 검색
# =============================================================
class SearchView(APIView):
    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]

        def event_stream():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            full_answer = ""
            start_time = time.time()
            db_query = None

            try:
                sources, answer_stream = loop.run_until_complete(run_rag_pipeline(query))

                # 소스 전송
                sources_data = [
                    {"title": s.title, "url": s.url, "snippet": s.snippet, "rank": s.rank}
                    for s in sources
                ]
                yield f"data: {json.dumps({'type': 'sources', 'data': sources_data}, ensure_ascii=False)}\n\n"

                # 스트리밍 청크 전송
                async def collect_stream():
                    nonlocal full_answer
                    async for chunk in answer_stream:
                        full_answer += chunk
                        yield chunk

                for chunk_text in loop.run_until_complete(_collect(answer_stream)):
                    full_answer += chunk_text
                    payload = json.dumps({"type": "chunk", "text": chunk_text}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"

                # DB 저장
                elapsed = round(time.time() - start_time, 2)
                db_query = SearchQuery.objects.create(
                    query=query,
                    answer=full_answer,
                    elapsed_seconds=elapsed,
                )
                for s in sources:
                    SearchSource.objects.create(
                        query=db_query,
                        title=s.title,
                        url=s.url,
                        snippet=s.snippet,
                        rank=s.rank,
                    )

                yield f"data: {json.dumps({'type': 'done', 'query_id': db_query.id, 'elapsed': elapsed})}\n\n"

            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                loop.close()

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


# =============================================================
# POST /api/search/image - 이미지 + 텍스트 검색
# =============================================================
class SearchImageView(APIView):
    def post(self, request):
        query = request.data.get("query", "").strip()
        image = request.FILES.get("image")

        if not query:
            return Response({"error": "검색어를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        if not image:
            return Response({"error": "이미지를 첨부해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        image_bytes = image.read()
        image_mime = image.content_type

        def event_stream():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            full_answer = ""
            start_time = time.time()

            try:
                async def collect():
                    chunks = []
                    async for chunk in generate_image_answer_stream(query, image_bytes, image_mime):
                        chunks.append(chunk)
                    return chunks

                chunks = loop.run_until_complete(collect())

                for chunk_text in chunks:
                    full_answer += chunk_text
                    payload = json.dumps({"type": "chunk", "text": chunk_text}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"

                # DB 저장
                elapsed = round(time.time() - start_time, 2)
                db_query = SearchQuery.objects.create(
                    query=query,
                    answer=full_answer,
                    elapsed_seconds=elapsed,
                    image_data=image_bytes,
                    image_mime=image_mime,
                )

                yield f"data: {json.dumps({'type': 'done', 'query_id': db_query.id, 'elapsed': elapsed})}\n\n"

            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                loop.close()

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


# =============================================================
# GET /api/history - 검색 히스토리
# =============================================================
class HistoryView(APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        queries = SearchQuery.objects.all()[:limit]
        serializer = SearchQuerySerializer(queries, many=True)
        return Response(serializer.data)


# =============================================================
# GET /api/history/{id} - 특정 검색 상세
# =============================================================
class HistoryDetailView(APIView):
    def get(self, request, query_id):
        try:
            query = SearchQuery.objects.prefetch_related("sources").get(id=query_id)
        except SearchQuery.DoesNotExist:
            return Response({"error": "검색 기록을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SearchQuerySerializer(query)
        return Response(serializer.data)


# 비동기 스트림을 리스트로 수집하는 헬퍼
async def _collect(stream):
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    return chunks