# =============================================================
# routers/search.py - 검색 관련 API 엔드포인트
# StreamingResponse로 LLM 답변을 실시간 전송합니다.
# =============================================================

import json
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from database import get_session
from models import SearchQuery, SearchSource, SearchRequest, SearchHistoryOut
from search_engine import run_rag_pipeline

router = APIRouter()


# =============================================================
# POST /api/v1/search - 핵심 검색 엔드포인트 (SSE 스트리밍)
#
# 응답 형식: Server-Sent Events (SSE)
#   - 소스 데이터: data: {"type": "sources", "data": [...]}
#   - 텍스트 청크: data: {"type": "chunk", "text": "..."}
#   - 완료 신호:   data: {"type": "done", "query_id": 123}
#
# 프론트엔드는 EventSource 또는 fetch + ReadableStream으로 수신
# =============================================================
@router.post("/search")
async def search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    사용자 쿼리를 받아 RAG 파이프라인을 실행하고
    SSE(Server-Sent Events) 형식으로 스트리밍 응답을 반환합니다.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")

    # -------------------------
    # 스트리밍 이벤트 제너레이터
    # -------------------------
    async def event_stream():
        start_time = time.time()
        full_answer = ""

        try:
            # RAG 파이프라인 실행 (검색 + 스트리밍 제너레이터 준비)
            sources, answer_stream = await run_rag_pipeline(query)

            # 1. 소스 정보를 먼저 전송 (프론트엔드에서 출처 패널 즉시 렌더링 가능)
            sources_data = [
                {"title": s.title, "url": s.url, "snippet": s.snippet, "rank": s.rank}
                for s in sources
            ]
            yield f"data: {json.dumps({'type': 'sources', 'data': sources_data}, ensure_ascii=False)}\n\n"

            # 2. LLM 답변을 청크 단위로 스트리밍 전송
            async for chunk_text in answer_stream:
                full_answer += chunk_text
                payload = json.dumps({"type": "chunk", "text": chunk_text}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            # 3. DB에 검색 기록 저장 (스트리밍 완료 후)
            elapsed = round(time.time() - start_time, 2)
            db_query = SearchQuery(
                query=query,
                answer=full_answer,
                elapsed_seconds=elapsed,
            )
            session.add(db_query)
            await session.commit()
            await session.refresh(db_query)

            # 소스도 DB에 저장
            for s in sources:
                db_source = SearchSource(
                    query_id=db_query.id,
                    title=s.title,
                    url=s.url,
                    snippet=s.snippet,
                    rank=s.rank,
                )
                session.add(db_source)
            await session.commit()

            # 4. 완료 신호 전송 (query_id로 히스토리 조회 가능)
            yield f"data: {json.dumps({'type': 'done', 'query_id': db_query.id, 'elapsed': elapsed})}\n\n"

        except Exception as e:
            # 에러 발생 시 클라이언트에 에러 이벤트 전송
            error_payload = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
        },
    )


# =============================================================
# GET /api/v1/history - 검색 히스토리 조회
# =============================================================
@router.get("/history", response_model=list[SearchHistoryOut])
async def get_history(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """최근 검색 기록을 반환합니다."""
    result = await session.exec(
        select(SearchQuery).order_by(SearchQuery.created_at.desc()).limit(limit)
    )
    return result.all()


# =============================================================
# GET /api/v1/history/{query_id} - 특정 검색 결과 조회
# =============================================================
@router.get("/history/{query_id}")
async def get_search_detail(
    query_id: int,
    session: AsyncSession = Depends(get_session),
):
    """특정 검색 ID에 대한 질문, 답변, 소스를 반환합니다."""
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