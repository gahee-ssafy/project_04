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

NOTEBOOK_CHAT_PROMPT = """당신은 경제학 오답노트 튜터입니다. 학생이 틀린 문제를 스스로 이해할 수 있도록 돕습니다.

## 응답 구조 (반드시 이 순서로)

학생이 설명하면:
1. **판별** — 학생의 설명이 맞는지 틀렸는지 명확하게 먼저 밝힌다.
   - 맞으면: "맞아요!" / "정확해요!" 로 시작
   - 틀리면: "아쉽게도 틀렸어요." / "조금 달라요." 로 시작
   - 일부만 맞으면: "반은 맞고 반은 달라요." 로 시작
2. **피드백** — 왜 맞는지 또는 어디서 틀렸는지 구체적으로 설명한다. 핵심 개념을 짚어준다.
3. **확인 또는 심화** — 이해가 완전히 됐으면 아래 형식으로 메모 제안을 반드시 포함한다.
   ```
   📝 메모 제안: [한 줄 핵심 요약]
   ```
   아직 이해가 부족하면 딱 하나의 질문으로 다음 단계를 유도한다. (메모 제안 없음)

## 금지 사항
- 판별 없이 바로 설명하거나 질문만 던지지 마세요.
- 학생 설명과 무관한 내용을 꺼내지 마세요.
- 한 번에 여러 질문을 하지 마세요.
- 3~5문장을 초과하지 마세요.

## 기타
- 수식은 LaTeX로 작성하세요. 인라인: $수식$, 블록: $$수식$$
- 한국어로만 답변합니다.
"""


def _parse_content(response) -> str:
    content = response.content
    if isinstance(content, list):
        text = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
    else:
        text = content
    return _normalize_math(text)


def _normalize_math(text: str) -> str:
    """Gemini가 \(...\) 또는 \[...\] 로 출력한 수식을 $...$, $$...$$ 로 변환."""
    import re
    text = re.sub(r'\\\[([\s\S]+?)\\\]', lambda m: f'$${m.group(1)}$$', text)
    text = re.sub(r'\\\(([\s\S]+?)\\\)', lambda m: f'${m.group(1)}$', text)
    return text


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
# 오답노트 메모 기반 AI 토론
# =============================================================
def notebook_chat(question: str, memo: str, solution: str, history: list,
                  image_bytes: bytes = None, image_mime: str = None) -> str:
    """메모를 읽고 소크라테스식 대화를 이어간다.
    history가 비어있으면 AI가 먼저 말을 건다 (opener).
    image_bytes가 있으면 학생 필기 이미지를 함께 전송.
    """
    messages = [SystemMessage(content=NOTEBOOK_CHAT_PROMPT)]

    # 문맥 주입
    ctx_parts = [f"[문제]\n{question}"]
    if solution:
        ctx_parts.append(f"[AI 풀이]\n{solution}")
    if memo:
        ctx_parts.append(f"[학생 메모]\n{memo}")
    messages.append(HumanMessage(content="\n\n".join(ctx_parts)))

    if not history:
        # opener: AI가 먼저 메모를 읽고 말 걸기
        if memo:
            opener = (
                f"메모에 '{memo}' 라고 적어두셨군요. "
                "좋아요, 그러면 이 문제에서 어떤 개념이 적용되는지, "
                "본인의 말로 설명해보실 수 있을까요? "
                "맞고 틀림을 바로 확인해드릴게요."
            )
        else:
            opener = (
                "이 문제를 틀리셨군요. "
                "이 문제가 어떤 개념을 묻는 문제라고 생각하셨는지, "
                "본인의 말로 먼저 설명해보세요. "
                "맞는 부분과 틀린 부분을 바로 짚어드릴게요."
            )
        messages.append(AIMessage(content=opener))
        return opener

    # 이후 대화: history 이어 붙이기
    messages.append(AIMessage(content=history[0]["content"]))  # opener
    for turn in history[1:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    # 마지막 학생 메시지 — 이미지가 있으면 멀티모달로 전송
    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime = image_mime or "image/png"
        messages.append(HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            {"type": "text", "text": "(학생이 필기한 내용입니다. 이 필기를 보고 이해도를 파악해서 피드백해주세요.)"},
        ]))

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
