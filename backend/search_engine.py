# =============================================================
# search_engine.py - 핵심 RAG(검색 증강 생성) 로직
# 1단계: 외부 검색 API로 웹 소스 수집
# 2단계: 소스를 컨텍스트로 Gemini에 전달해 스트리밍 답변 생성
# =============================================================

import os
import asyncio
import httpx
from typing import AsyncGenerator
import google.generativeai as genai

# -------------------------------------------------------------
# 환경 변수에서 API 키 로드
# -------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")  # 웹 검색 API (serper.dev)

# Gemini 클라이언트 초기화
genai.configure(api_key=GEMINI_API_KEY)


# -------------------------------------------------------------
# SearchResult - 검색 결과 하나를 담는 간단한 데이터 클래스
# -------------------------------------------------------------
class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, rank: int):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.rank = rank


# =============================================================
# STEP 1: 웹 검색 - Serper API를 통해 실시간 웹 결과 수집
# Serper는 Google 검색 결과를 JSON으로 반환하는 저비용 API
# 대안: Tavily API, Bing Search API 등
# =============================================================
async def fetch_web_results(query: str, num_results: int = 5) -> list[SearchResult]:
    """
    Serper.dev API를 사용해 웹 검색 결과를 비동기로 가져옵니다.
    반환: SearchResult 객체 리스트
    """
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "num": num_results,
        "hl": "ko",  # 한국어 우선 결과
        "gl": "kr",  # 한국 지역 결과
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            print(f"⚠️ 검색 API 오류: {e}")
            return []

    results = []
    # Serper 응답의 'organic' 키에 일반 검색 결과가 담겨 있음
    for i, item in enumerate(data.get("organic", [])[:num_results]):
        results.append(SearchResult(
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
            rank=i + 1,
        ))

    return results


# =============================================================
# STEP 2: 컨텍스트 구성 - 검색 결과를 LLM 프롬프트용 텍스트로 변환
# =============================================================
def build_context(results: list[SearchResult]) -> str:
    """
    검색 결과 리스트를 번호 매긴 컨텍스트 블록으로 조합합니다.
    LLM이 출처를 인식하고 답변에 인용번호를 달 수 있도록 구조화합니다.
    """
    if not results:
        return "검색 결과를 찾을 수 없습니다."

    context_parts = []
    for r in results:
        context_parts.append(
            f"[{r.rank}] 제목: {r.title}\n"
            f"    URL: {r.url}\n"
            f"    내용: {r.snippet}"
        )

    return "\n\n".join(context_parts)


# =============================================================
# STEP 3: Gemini 스트리밍 답변 생성
# gemini-2.0-flash 모델로 RAG 기반 답변을 실시간 스트리밍
# =============================================================
async def generate_answer_stream(
    query: str,
    context: str,
) -> AsyncGenerator[str, None]:
    """
    Gemini Flash에 검색 컨텍스트를 주입한 뒤,
    답변을 청크(chunk) 단위로 비동기 스트리밍합니다.

    FastAPI StreamingResponse와 함께 사용됩니다.
    """
    # -------------------------
    # 시스템 프롬프트: LLM의 역할과 출력 형식 정의
    # -------------------------
    system_prompt = """당신은 정확하고 신뢰할 수 있는 AI 검색 어시스턴트입니다.
제공된 검색 결과(컨텍스트)를 바탕으로 사용자의 질문에 답변하세요.

규칙:
1. 반드시 제공된 컨텍스트에 근거해서 답변하세요.
2. 답변 내에 출처를 [1], [2] 형식으로 인용하세요.
3. 명확하고 구조적으로 작성하되, 불필요한 반복은 피하세요.
4. 컨텍스트에 답이 없으면 솔직하게 모른다고 밝히세요.
5. 한국어로 답변하세요."""

    # -------------------------
    # 사용자 프롬프트: 컨텍스트 + 질문 결합
    # -------------------------
    user_prompt = f"""[검색 컨텍스트]
{context}

[질문]
{query}

위 검색 결과를 바탕으로 질문에 대한 정확하고 도움이 되는 답변을 작성해주세요."""

    # -------------------------
    # Gemini API 스트리밍 호출
    # gemini-2.0-flash: 빠른 응답 속도, 비용 효율적
    # -------------------------
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_prompt,
    )

    # 동기 스트리밍을 비동기로 실행 (google-genai SDK는 동기 기반)
    # run_in_executor로 별도 스레드에서 실행해 이벤트 루프 블로킹 방지
    loop = asyncio.get_event_loop()

    def _sync_stream():
        return model.generate_content(
            user_prompt,
            stream=True,
            generation_config={
                "temperature": 0.3,       # 낮을수록 일관성 있는 답변
                "max_output_tokens": 2048,
            },
        )

    response = await loop.run_in_executor(None, _sync_stream)

    # 스트리밍 청크를 하나씩 yield
    for chunk in response:
        if chunk.text:
            yield chunk.text


# =============================================================
# run_rag_pipeline - 전체 RAG 파이프라인을 조율하는 메인 함수
# routers/search.py에서 호출됩니다.
# =============================================================
async def run_rag_pipeline(
    query: str,
) -> tuple[list[SearchResult], AsyncGenerator[str, None]]:
    """
    1. 웹 검색으로 소스 수집
    2. 컨텍스트 구성
    3. 스트리밍 제너레이터 반환

    반환값:
        - sources: DB 저장 및 프론트엔드 표시용 소스 리스트
        - stream: 답변 텍스트 청크를 비동기로 yield하는 제너레이터
    """
    # STEP 1: 웹 검색
    sources = await fetch_web_results(query, num_results=5)

    # STEP 2: 컨텍스트 구성
    context = build_context(sources)

    # STEP 3: 스트리밍 제너레이터 생성 (실제 실행은 라우터에서 iterate할 때 시작)
    stream = generate_answer_stream(query, context)

    return sources, stream
