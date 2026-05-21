"""Gemini LLM + 임베딩 서비스 (search.py에서 이식)"""
import os
import json
import base64
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from google import genai as google_genai

load_dotenv()

_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=0.3,
    google_api_key=_api_key,
)
_embed_client = google_genai.Client(api_key=_api_key)
_EMBED_MODEL = "models/gemini-embedding-exp-03-07"

# =============================================================
# 시스템 프롬프트
# =============================================================
TUTOR_PROMPT = """당신은 학생 옆에서 함께 문제를 보는 경제학 전문 튜터입니다.

## 응답 원칙
1. 이미지가 있으면 학생의 필기, 동그라미, 취소선, 메모까지 꼼꼼히 읽으세요.
2. 학생이 틀리기 쉬운 포인트, 헷갈리기 쉬운 개념을 우선적으로 깊이 설명하세요.
3. 수식은 LaTeX 형식으로 작성하세요. 인라인: $수식$, 블록: $$수식$$
4. 응답 구조: 주제 소개 → 정답 확인 → 선지별 해설 (함정 중심)
5. 딱딱한 강의체 금지. 공감하는 말투로 시작하세요.
6. 면책 문구는 절대 포함하지 마세요.

항상 한국어로 답변합니다.
"""

DEBATE_PROMPT = """당신은 경제학 토론 상대입니다.
소크라테스식 문답으로 깊이 있는 논증을 이끌어냅니다.

규칙:
- 학생의 주장을 먼저 인정한 뒤, 논리적 허점이나 심화 질문을 던지세요.
- 틀린 부분은 직접 지적하되 반문으로 유도하세요.
- 학생이 옳으면 솔직히 인정하고 추가 개념을 연결하세요.
- 모든 답변은 2-4문단, 마지막 문장은 반드시 질문으로 끝내세요.
- 한국어로만 답변합니다.
"""


def _parse_content(response) -> str:
    content = response.content
    if isinstance(content, list):
        return "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
    return content


# =============================================================
# 풀이 생성
# =============================================================
def ask(
    query: str,
    image_bytes: bytes = None,
    image_mime: str = None,
    chat_history: list = None,
) -> str:
    messages = [SystemMessage(content=TUTOR_PROMPT)]

    if chat_history:
        for turn in chat_history:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            else:
                messages.append(AIMessage(content=turn["content"]))

    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        human = HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{img_b64}"}},
            {"type": "text", "text": query},
        ])
    else:
        human = HumanMessage(content=query)

    messages.append(human)
    return _parse_content(llm.invoke(messages))


# =============================================================
# AI 토론
# =============================================================
def debate_reply(problem: str, solution: str, history: list, user_msg: str) -> str:
    messages = [SystemMessage(content=DEBATE_PROMPT)]
    ctx = f"[원래 문제]\n{problem}\n\n[AI 풀이]\n{solution}"
    messages.append(HumanMessage(content=ctx))
    messages.append(AIMessage(content="알겠습니다. 위 풀이를 기반으로 토론할 준비가 됐어요. 어떤 부분이 의문이신가요?"))

    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    messages.append(HumanMessage(content=user_msg))
    return _parse_content(llm.invoke(messages))


# =============================================================
# 학습 요약
# =============================================================
def summarize_history(sessions: list) -> str:
    _SKIP = ("[심화학습]", "[유사문제]", "[토론]", "[오답노트]", "[모의고사]")
    filtered = [
        s for s in sessions
        if not str(s["question"]).startswith(_SKIP) and str(s.get("answer") or "").strip()
    ]
    if not filtered:
        return "요약할 실제 질문 기록이 없어요."

    questions = "\n".join([f"- {s['question']}" for s in filtered])
    prompt = f"""다음은 학생이 질문한 내용 목록이에요.

{questions}

아래 형식으로 학습 요약을 작성해주세요.

📌 자주 질문한 주제
→ 어떤 개념을 많이 물어봤는지

🔍 학습 패턴
→ 어떤 유형의 문제를 주로 다뤘는지

💡 추천 학습 방향
→ 더 공부하면 좋을 개념

한국어로 간결하게 작성해주세요."""

    return _parse_content(llm.invoke([HumanMessage(content=prompt)]))


# =============================================================
# 임베딩
# =============================================================
def get_embedding(text: str) -> list:
    result = _embed_client.models.embed_content(model=_EMBED_MODEL, contents=text)
    return result.embeddings[0].values


def cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    return 0.0 if (norm_a == 0 or norm_b == 0) else dot / (norm_a * norm_b)
