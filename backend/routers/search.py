import json
import time
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from database import get_session, AsyncSessionLocal  # AsyncSessionLocal 추가
from models import SearchQuery, SearchSource, SearchRequest, SearchHistoryOut
from search_engine import run_rag_pipeline, generate_image_answer_stream

router = APIRouter()


# =============================================================
# POST /api/v1/search
# =============================================================
@router.post("/search")
async def search(request: SearchRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")

    async def event_stream():
        start_time = time.time()
        full_answer = ""

        try:
            sources, answer_stream = await run_rag_pipeline(query)

            sources_data = [
                {"title": s.title, "url": s.url, "snippet": s.snippet, "rank": s.rank}
                for s in sources
            ]
            yield f"data: {json.dumps({'type': 'sources', 'data': sources_data}, ensure_ascii=False)}\n\n"

            async for chunk_text in answer_stream:
                full_answer += chunk_text
                payload = json.dumps({"type": "chunk", "text": chunk_text}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            # 스트리밍 완료 후 세션 직접 열어서 저장
            elapsed = round(time.time() - start_time, 2)
            async with AsyncSessionLocal() as session:
                db_query = SearchQuery(
                    query=query,
                    answer=full_answer,
                    elapsed_seconds=elapsed,
                )
                session.add(db_query)
                await session.commit()
                await session.refresh(db_query)

                for s in sources:
                    session.add(SearchSource(
                        query_id=db_query.id,
                        title=s.title,
                        url=s.url,
                        snippet=s.snippet,
                        rank=s.rank,
                    ))
                await session.commit()

            yield f"data: {json.dumps({'type': 'done', 'query_id': db_query.id, 'elapsed': elapsed})}\n\n"

        except Exception as e:
            error_payload = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =============================================================
# POST /api/v1/search/image
# =============================================================
@router.post("/search/image")
async def search_with_image(
    query: str = Form(...),
    image: UploadFile = File(...),
):
    image_bytes = await image.read()
    image_mime = image.content_type

    async def event_stream():
        full_answer = ""
        start_time = time.time()

        try:
            async for chunk_text in generate_image_answer_stream(query, image_bytes, image_mime):
                full_answer += chunk_text
                payload = json.dumps({"type": "chunk", "text": chunk_text}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            # 스트리밍 완료 후 세션 직접 열어서 저장
            elapsed = round(time.time() - start_time, 2)
            async with AsyncSessionLocal() as session:
                db_query = SearchQuery(
                    query=query,
                    answer=full_answer,
                    elapsed_seconds=elapsed,
                    image_data=image_bytes,
                    image_mime=image_mime,
                )
                session.add(db_query)
                await session.commit()
                await session.refresh(db_query)

            yield f"data: {json.dumps({'type': 'done', 'query_id': db_query.id, 'elapsed': elapsed})}\n\n"

        except Exception as e:
            error_payload = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =============================================================
# GET /api/v1/history
# =============================================================
@router.get("/history", response_model=list[SearchHistoryOut])
async def get_history(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(
        select(SearchQuery).order_by(SearchQuery.created_at.desc()).limit(limit)
    )
    return result.all()


# =============================================================
# GET /api/v1/history/{query_id}
# =============================================================
@router.get("/history/{query_id}")
async def get_search_detail(
    query_id: int,
    session: AsyncSession = Depends(get_session),
):
    query_record = await session.get(SearchQuery, query_id)
    if not query_record:
        raise HTTPException(status_code=404, detail="검색 기록을 찾을 수 없습니다.")

    sources = await session.exec(
        select(SearchSource)
        .where(SearchSource.query_id == query_id)
        .order_by(SearchSource.rank)
    )

    return {
        "query": query_record,
        "sources": sources.all(),
    }