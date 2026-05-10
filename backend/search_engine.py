import os
import asyncio
from typing import AsyncGenerator
import google.generativeai as genai

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "mock_key")


class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, rank: int):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.rank = rank


# =============================================================
# STEP 1: 웹 검색 Mock (TODO: Serper 연결)
# =============================================================
async def fetch_web_results(query: str, num_results: int = 5) -> list[SearchResult]:
    await asyncio.sleep(0.5)
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
# STEP 2: 컨텍스트 구성
# =============================================================
def build_context(results: list[SearchResult]) -> str:
    if not results:
        return "검색 결과를 찾을 수 없습니다."
    context_parts = [f"[{r.rank}] {r.title}: {r.snippet}" for r in results]
    return "\n".join(context_parts)


# =============================================================
# STEP 3: Gemini 스트리밍 (텍스트 / 이미지 통합)
# =============================================================
async def generate_answer_stream(
    query: str,
    context: str = "",
    image_bytes: bytes = None,
    image_mime: str = None,  # "image/jpeg", "image/png" 등
) -> AsyncGenerator[str, None]:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    system_instruction = (
        "당신은 친절한 AI 어시스턴트입니다. "
        "이미지와 질문을 함께 분석해서 한국어로 답변하세요."
        if image_bytes else
        "당신은 친절한 AI 검색 어시스턴트입니다. "
        "제공된 컨텍스트를 바탕으로 한국어로 답변하세요."
    )

    model = genai.GenerativeModel(
        model_name="gemini-3.1-flash-lite",
        system_instruction=system_instruction
    )

    # 이미지 유무에 따라 prompt 형태만 분기
    if image_bytes:
        prompt = [
            {"mime_type": image_mime, "data": image_bytes},
            f"{context}\n\n{query}" if context else query,
        ]
    else:
        prompt = f"[검색 컨텍스트]\n{context}\n\n[질문]\n{query}"

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: model.generate_content(prompt, stream=True)
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text


# =============================================================
# 메인 파이프라인
# =============================================================
async def run_rag_pipeline(
    query: str,
    image_bytes: bytes = None,
    image_mime: str = None,
) -> tuple[list[SearchResult], AsyncGenerator[str, None]]:
    sources = await fetch_web_results(query, num_results=5)
    context = build_context(sources)
    stream = generate_answer_stream(query, context, image_bytes, image_mime)
    return sources, stream