"""MonoGPT API 기반 AI 서비스"""
import os
import uuid
import base64
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.environ.get("MONOGPT_API_KEY")
_BASE_URL = "https://monogpt.kr/api/monorouter/v1/gemini"
_MODEL = "gemini-3.5-flash"

# =============================================================
# 시스템 프롬프트
# =============================================================
TUTOR_PROMPT = """당신은 학생 옆에서 함께 문제를 보는 NCS 직업기초능력 전문 튜터입니다.

## 응답 원칙
1. 이미지가 있으면 학생의 필기, 동그라미, 취소선, 메모까지 꼼꼼히 읽으세요.
2. 학생이 틀리기 쉬운 포인트, 헷갈리기 쉬운 개념을 우선적으로 깊이 설명하세요.
3. 응답 구조: 주제 소개 → 정답 확인 → 선지별 해설 (함정 중심)
4. 딱딱한 강의체 금지. 공감하는 말투로 시작하세요.
5. 면책 문구는 절대 포함하지 마세요.

항상 한국어로 답변합니다.
"""

NOTEBOOK_CHAT_PROMPT = """당신은 NCS 직업기초능력 오답노트 튜터입니다. 학생이 틀린 문제를 스스로 이해할 수 있도록 돕습니다.

## 입력 유형 판단 (먼저 판단하세요)

**① 학생이 개념/답을 설명하는 경우** (예: "의사소통은 ~이에요", "이 문제는 ~때문에 틀렸어요")
→ 아래 판별 구조로 응답

**② 학생이 질문하는 경우** (예: "이 개념이 뭐예요?", "왜 틀렸나요?")
→ 판별 없이 바로 설명

**③ 학생이 요청하는 경우** (예: "메모로 만들어주세요", "정리해줘")
→ 판별 없이 요청 수행

---

## ①번 판별 구조

1. **판별** — 맞으면 "맞아요!" / 틀리면 "아쉽게도 틀렸어요." / 일부만 맞으면 "반은 맞아요."
2. **피드백** — 왜 맞는지 또는 어디서 틀렸는지 핵심만 짚는다.
3. **다음 단계** — 이해 완료면 📝 메모 제안 포함. 부족하면 질문 하나로 유도.

```
📝 메모 제안: [한 줄 핵심 요약]
```

## 금지 사항
- 한 번에 여러 질문을 하지 마세요.
- 3~5문장을 초과하지 마세요.
- 한국어로만 답변합니다.
"""

NOTEBOOK_STUDENT_PROMPT = """당신은 NCS 직업기초능력을 전혀 모르는 중학생입니다. 파인만 기법 학습을 위해 선생님(사용자)에게 개념을 배우는 역할입니다.

## 당신의 캐릭터
- NCS 개념을 처음 듣는 중학생
- 솔직하고 직접적으로 모른다고 말함
- 한 번에 질문 하나만 함
- 짧고 단순한 문장을 씀

## 대화 패턴 (순환)
1. **모르겠다 → 질문** — "그게 무슨 뜻이에요?", "왜요?", "예를 들어주세요"
2. **이해했다 → 확인** — "아, 그러면 ~라는 말이에요?", "그럼 이 경우엔 어떻게 돼요?"
3. **가끔 틀린 이해** — "아, 그럼 ~이라는 거죠?" (잘못 이해한 척해서 선생님이 교정하게 유도)

## 금지 사항
- 절대로 스스로 개념을 설명하거나 정답을 알려주지 마세요.
- "잘 설명해주셨네요" 같은 과한 칭찬은 하지 마세요.
- 한 번에 두 개 이상 질문하지 마세요.
- 3문장을 초과하지 마세요.
- 한국어로만 답변합니다.
"""


# =============================================================
# MonoGPT HTTP 호출
# =============================================================
def _chat(messages: list[dict]) -> str:
    system_instruction = None
    contents = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    body = {"contents": contents}
    if system_instruction:
        body["system_instruction"] = system_instruction

    headers = {
        "x-goog-api-key": _API_KEY,
        "Content-Type": "application/json",
    }
    url = f"{_BASE_URL}/v1beta/models/{_MODEL}:generateContent"
    resp = httpx.post(url, headers=headers, json=body, timeout=60)
    if not resp.is_success:
        print(f"[MonoGPT ERROR] status={resp.status_code} body={resp.text}")
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _normalize_math(text: str) -> str:
    text = re.sub(r'\\\[([\s\S]+?)\\\]', lambda m: f'$${m.group(1)}$$', text)
    text = re.sub(r'\\\(([\s\S]+?)\\\)', lambda m: f'${m.group(1)}$', text)
    return text


def _build_messages(system: str, turns: list[dict]) -> list[dict]:
    msgs = [{"role": "system", "content": system}]
    msgs.extend(turns)
    return msgs


# generate.py 에서 llm.invoke(messages) 형태로 쓰므로 호환 래퍼 제공
class _LLMCompat:
    def invoke(self, lc_messages) -> "_FakeResponse":
        msgs = []
        for m in lc_messages:
            role = "system" if m.__class__.__name__ == "SystemMessage" else \
                   "assistant" if m.__class__.__name__ == "AIMessage" else "user"
            content = m.content
            if isinstance(content, list):
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            msgs.append({"role": role, "content": content})
        reply = _chat(msgs)
        return _FakeResponse(reply)

    def stream(self, lc_messages):
        yield self.invoke(lc_messages)


class _FakeResponse:
    def __init__(self, text: str):
        self.content = text


llm = _LLMCompat()


# =============================================================
# 풀이 생성
# =============================================================
def ask(
    query: str,
    image_bytes: bytes = None,
    image_mime: str = None,
    chat_history: list = None,
) -> str:
    turns = []
    if chat_history:
        for turn in chat_history:
            turns.append({"role": turn["role"], "content": turn["content"]})

    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        content = f"data:{image_mime};base64,{img_b64}\n\n{query}"
        turns.append({"role": "user", "content": content})
    else:
        turns.append({"role": "user", "content": query})

    msgs = _build_messages(TUTOR_PROMPT, turns)
    return _normalize_math(_chat(msgs))


# =============================================================
# 오답노트 AI 토론
# =============================================================
def _get_notebook_opener(memo: str, mode: str = "teacher") -> str:
    if mode == "student":
        return "선생님, 저 이 문제 전혀 모르겠어요. 이 문제가 어떤 개념을 묻는 건지 설명해줄 수 있어요?"
    if memo:
        return (
            f"메모에 '{memo}' 라고 적어두셨군요. "
            "좋아요, 그러면 이 문제에서 어떤 개념이 적용되는지, "
            "본인의 말로 설명해보실 수 있을까요? "
            "맞고 틀림을 바로 확인해드릴게요."
        )
    return (
        "이 문제를 틀리셨군요. "
        "이 문제가 어떤 개념을 묻는 문제라고 생각하셨는지, "
        "본인의 말로 먼저 설명해보세요. "
        "맞는 부분과 틀린 부분을 바로 짚어드릴게요."
    )


def _build_notebook_turns(question: str, memo: str, solution: str, history: list,
                           user_message: str = "", image_bytes: bytes = None,
                           image_mime: str = None) -> list[dict]:
    turns = []
    ctx_parts = [f"[문제]\n{question}"]
    if solution:
        ctx_parts.append(f"[AI 풀이]\n{solution}")
    if memo:
        ctx_parts.append(f"[학생 메모]\n{memo}")
    turns.append({"role": "user", "content": "\n\n".join(ctx_parts)})
    turns.append({"role": "assistant", "content": history[0]["content"]})
    for turn in history[1:]:
        turns.append({"role": turn["role"], "content": turn["content"]})

    if image_bytes:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime = image_mime or "image/png"
        content = f"data:{mime};base64,{img_b64}\n\n{user_message or '(학생이 필기한 내용입니다. 이 필기를 보고 이해도를 파악해서 피드백해주세요.)'}"
        turns.append({"role": "user", "content": content})
    elif user_message:
        turns.append({"role": "user", "content": user_message})

    return turns


def notebook_chat(question: str, memo: str, solution: str, history: list,
                  user_message: str = "", image_bytes: bytes = None,
                  image_mime: str = None, mode: str = "teacher") -> str:
    if not history:
        return _get_notebook_opener(memo, mode)
    system = NOTEBOOK_STUDENT_PROMPT if mode == "student" else NOTEBOOK_CHAT_PROMPT
    turns = _build_notebook_turns(question, memo, solution, history, user_message, image_bytes, image_mime)
    msgs = _build_messages(system, turns)
    return _normalize_math(_chat(msgs))


def notebook_chat_stream(question: str, memo: str, solution: str, history: list,
                         user_message: str = "", image_bytes: bytes = None,
                         image_mime: str = None, mode: str = "teacher"):
    if not history:
        yield _get_notebook_opener(memo, mode)
        return
    system = NOTEBOOK_STUDENT_PROMPT if mode == "student" else NOTEBOOK_CHAT_PROMPT
    turns = _build_notebook_turns(question, memo, solution, history, user_message, image_bytes, image_mime)
    msgs = _build_messages(system, turns)
    yield _normalize_math(_chat(msgs))


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

    return _normalize_math(_chat([{"role": "user", "content": prompt}]))

