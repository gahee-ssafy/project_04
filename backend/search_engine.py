import os
import asyncio
from typing import AsyncGenerator

# -------------------------------------------------------------
# STEP 0: Mock 모드 설정 (API 키 체크 생략)
# -------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "mock_key")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "mock_key")

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, rank: int):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.rank = rank

# =============================================================
# STEP 1: 웹 검색 Mock - Serper 호출 대신 가짜 결과 반환
# =============================================================
async def fetch_web_results(query: str, num_results: int = 5) -> list[SearchResult]:
    """네트워크 호출 없이 즉시 가짜 검색 결과 3개를 반환합니다."""
    # 실제 httpx 호출 부분은 주석 처리하여 부하를 방지합니다.
    await asyncio.sleep(0.5) # 실제 검색하는 척 0.5초 대기
    
    mock_results = [
        SearchResult(
            title=f"{query}에 대한 첫 번째 검색 결과",
            url="https://example.com/1",
            snippet=f"이것은 '{query}'와 관련된 샘플 문서의 내용입니다.",
            rank=1
        ),
        SearchResult(
            title=f"{query} 정보 위키",
            url="https://example.com/2",
            snippet=f"사용자가 입력한 '{query}'에 대한 백과사전식 설명입니다.",
            rank=2
        )
    ]
    return mock_results[:num_results]

# =============================================================
# STEP 2: 컨텍스트 구성 (기존 로직 유지)
# =============================================================
def build_context(results: list[SearchResult]) -> str:
    if not results:
        return "검색 결과를 찾을 수 없습니다."
    context_parts = [f"[{r.rank}] {r.title}: {r.snippet}" for r in results]
    return "\n".join(context_parts)

# =============================================================
# STEP 3: Gemini 스트리밍 Mock - API 호출 없이 한 글자씩 출력
# =============================================================
async def generate_answer_stream(
    query: str,
    context: str,
) -> AsyncGenerator[str, None]:
    """Gemini API 호출 없이 미리 준비된 가짜 답변을 한 글자씩 스트리밍합니다."""
    
    full_response = f"질문하신 '{query}'에 대해 검색한 결과입니다. [1], [2] 출처를 참고했을 때, 현재는 Mock 모드로 동작 중이므로 실제 AI 답변 대신 이 메시지가 출력됩니다. API 키를 설정하면 실제 Gemini-2.0-flash의 답변이 나옵니다."

    # 한 글자씩(또는 단어씩) 쪼개서 스트리밍 흉내내기
    for word in full_response.split():
        await asyncio.sleep(0.1) # 0.1초마다 단어 출력 (스트리밍 느낌)
        yield word + " "

# =============================================================
# run_rag_pipeline - 메인 파이프라인 (Mock 버전)
# =============================================================
async def run_rag_pipeline(
    query: str,
) -> tuple[list[SearchResult], AsyncGenerator[str, None]]:
    # 1. 가짜 검색 결과 수집
    sources = await fetch_web_results(query, num_results=5)

    # 2. 컨텍스트 구성
    context = build_context(sources)

    # 3. 가짜 스트리밍 제너레이터 반환
    stream = generate_answer_stream(query, context)

    return sources, stream