"""
학습일지 보고서 생성 서비스
- 통계·개념·인용 → 템플릿 (항상 최신 데이터)
- 학습 패턴 분석·추천 학습 방향 → Gemini (DB 캐시, 재생성 선택 가능)
"""
import json
import re
from collections import Counter
from datetime import datetime

from database import get_conn, get_learning_report, save_learning_report

# ─── 경제학 개념 사전 ────────────────────────────────────────────
ECON_CONCEPTS = {
    "수요": ["수요곡선", "수요량", "수요 변화", "수요가", "수요는", "수요를", "수요의"],
    "공급": ["공급곡선", "공급량", "공급 변화", "공급가", "공급는", "공급를", "공급의"],
    "탄력성": ["탄력성", "탄력적", "비탄력", "가격탄력"],
    "GDP·국민소득": ["GDP", "국내총생산", "국민소득", "GNP", "경제성장률"],
    "물가·인플레이션": ["물가", "인플레이션", "인플레", "CPI", "디플레이션", "디플레"],
    "금리·이자율": ["금리", "이자율", "기준금리", "실질금리", "명목금리"],
    "환율": ["환율", "절상", "절하", "평가절상", "평가절하", "달러"],
    "재정정책": ["재정정책", "정부지출", "조세", "재정승수", "국채"],
    "통화정책": ["통화정책", "통화량", "본원통화", "통화승수", "공개시장조작"],
    "소비·저축": ["소비함수", "한계소비성향", "저축률", "가처분소득"],
    "투자": ["투자함수", "한계효율", "투자승수", "가속도원리"],
    "무역·국제수지": ["경상수지", "무역수지", "자본수지", "수출입"],
    "비교우위": ["비교우위", "절대우위", "특화", "기회비용"],
    "시장실패": ["시장실패", "외부효과", "공공재", "독점", "과점", "정보비대칭"],
    "IS-LM": ["IS곡선", "LM곡선", "IS-LM", "유동성함정"],
    "총수요·총공급": ["총수요", "총공급", "AD곡선", "AS곡선", "AD-AS"],
    "필립스곡선": ["필립스곡선", "필립스 곡선"],
    "케인즈": ["케인즈", "케인지안", "유효수요", "절약의 역설"],
    "승수효과": ["승수효과", "지출승수", "세금승수", "균형재정승수"],
    "최저임금·가격규제": ["최저임금", "최고가격", "가격하한", "가격상한"],
}

# ─── DB 조회 ─────────────────────────────────────────────────────
def _get_raw_data(user_id: int) -> dict:
    conn = get_conn()
    notebook_rows = conn.execute(
        """SELECT s.id, s.question, s.created_at, COALESCE(m.memo, '') AS memo
           FROM sessions s
           LEFT JOIN memos m ON m.session_id = s.id AND m.user_id = s.user_id
           WHERE s.user_id = ?
             AND (s.question LIKE '[오답노트]%' OR s.question LIKE '[모의고사]%')
           ORDER BY s.created_at ASC""",
        (user_id,),
    ).fetchall()
    chat_rows = conn.execute(
        "SELECT notebook_session_id, messages FROM notebook_chats WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    conn.close()

    notebooks = [dict(r) for r in notebook_rows]
    chats_by_session = {}
    for r in chat_rows:
        try:
            msgs = json.loads(r["messages"])
        except Exception:
            msgs = []
        chats_by_session[r["notebook_session_id"]] = msgs

    return {"notebooks": notebooks, "chats_by_session": chats_by_session}


# ─── 통계 ────────────────────────────────────────────────────────
def _calc_stats(notebooks: list, chats_by_session: dict) -> dict:
    total = len(notebooks)
    if total == 0:
        return {"total": 0}
    memo_count   = sum(1 for n in notebooks if n["memo"].strip())
    chat_sessions = sum(1 for n in notebooks if n["id"] in chats_by_session)
    student_msg_count = sum(
        1 for msgs in chats_by_session.values()
        for m in msgs if m.get("role") == "user"
    )
    dates = [n["created_at"][:10] for n in notebooks if n.get("created_at")]
    return {
        "total": total,
        "memo_count": memo_count,
        "memo_rate": round(memo_count / total * 100) if total else 0,
        "chat_sessions": chat_sessions,
        "chat_rate": round(chat_sessions / total * 100) if total else 0,
        "student_msg_count": student_msg_count,
        "first_date": min(dates) if dates else None,
        "last_date":  max(dates) if dates else None,
        "active_days": len(set(dates)),
    }


# ─── 텍스트 수집 ─────────────────────────────────────────────────
def _collect_text(notebooks, chats_by_session) -> str:
    parts = [n["memo"] for n in notebooks if n["memo"].strip()]
    for msgs in chats_by_session.values():
        parts += [m["content"] for m in msgs if m.get("role") == "user"]
    return " ".join(parts)


# ─── 개념 추출 ───────────────────────────────────────────────────
def _extract_concepts(text: str) -> list[tuple[str, int]]:
    counts = Counter()
    for concept, keywords in ECON_CONCEPTS.items():
        for kw in keywords:
            counts[concept] += text.count(kw)
    result = [(c, n) for c, n in counts.items() if n > 0]
    result.sort(key=lambda x: -x[1])
    return result[:6]


# ─── 학생 직접 질문 추출 ─────────────────────────────────────────
def _extract_student_quotes(chats_by_session: dict, limit_for_display: int = 5) -> list[str]:
    """학생 질문 전체 추출. display용은 앞 5개만 쓰고, AI 분석용은 전체 반환."""
    quotes, seen = [], set()
    for msgs in chats_by_session.values():
        for m in msgs:
            if m.get("role") == "user":
                text = m["content"].strip()
                if len(text) >= 10 and text not in seen:
                    seen.add(text)
                    quotes.append(text)
    return quotes


def _extract_student_quotes_for_display(chats_by_session: dict) -> list[str]:
    return _extract_student_quotes(chats_by_session)[:5]


# ─── AI 프롬프트 ────────────────────────────────────────────────
_AI_PROMPT = """아래는 한 학생이 경제학 오답노트에 직접 적은 메모와 AI 토론에서 한 질문들이에요.

{data}

이 내용만 보고 딱 두 가지를 JSON으로만 답해주세요. 다른 말은 절대 하지 마세요.

규칙:
- 반드시 위에 있는 내용(메모, 질문)만 근거로 삼으세요.
- 없는 내용을 언급하거나 "메모가 없어요", "질문이 적어요" 같은 말은 절대 하지 마세요.
- 말투: 친한 선배처럼 편하게. "~네요", "~하더라고요", "~해봐요" 같은 자연스러운 어투.
- 딱딱한 강의체, 면책 문구, 인사말 금지.

{{
  "pattern": "위의 메모와 질문 내용을 근거로 이 학생의 학습 패턴을 2~3문장으로. 어떤 개념을 헷갈려하는지, 어떤 방식으로 이해하려는지 구체적으로.",
  "advice": "100자 이내. 위 질문이나 메모 중 하나를 따옴표로 직접 인용해서 콕 집어 조언 1가지만."
}}"""


def _build_data_section(stats, concepts, quotes, notebooks) -> str:
    lines = []

    # 실제 메모 내용 (전부)
    memos = [n["memo"].strip() for n in notebooks if n.get("memo", "").strip()]
    if memos:
        lines.append("[학생이 직접 작성한 메모]")
        for m in memos:
            lines.append(f'  - "{m}"')

    # 실제 질문 내용 (전부)
    if quotes:
        lines.append("\n[AI 토론에서 학생이 한 질문]")
        for q in quotes:
            lines.append(f'  - "{q}"')

    return "\n".join(lines) if lines else "(아직 메모와 질문 내용이 없습니다)"


def _call_gemini(data_section: str) -> tuple[str, str]:
    """Gemini 호출 → (ai_pattern, ai_advice) 반환."""
    from services.ai import llm, _normalize_math
    from langchain_core.messages import HumanMessage

    prompt = _AI_PROMPT.format(data=data_section)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content
    if isinstance(raw, list):
        raw = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in raw)

    # JSON 파싱
    try:
        m = re.search(r'\{[\s\S]*\}', raw)
        obj = json.loads(m.group()) if m else {}
        pattern = _normalize_math(obj.get("pattern", "").strip())
        advice  = _normalize_math(obj.get("advice",  "").strip())
    except Exception:
        pattern = _normalize_math(raw.strip())
        advice  = ""

    return pattern, advice


# ─── 메인 ────────────────────────────────────────────────────────
def generate_report(user_id: int, regenerate: bool = False) -> dict:
    """통합 학습일지 보고서.
    - 통계·개념·인용: 항상 최신 계산
    - AI 분석: DB 캐시 우선, regenerate=True 이면 재생성 후 저장
    """
    raw       = _get_raw_data(user_id)
    notebooks = raw["notebooks"]
    chats     = raw["chats_by_session"]

    if not notebooks:
        return {
            "has_data": False,
            "message": "아직 오답노트에 기록된 문제가 없어요. 모의고사를 풀고 틀린 문제를 추가해보세요!",
        }

    stats          = _calc_stats(notebooks, chats)
    text           = _collect_text(notebooks, chats)
    concepts       = _extract_concepts(text)
    quotes_display = _extract_student_quotes_for_display(chats)   # 화면 표시용 (5개)
    quotes_all     = _extract_student_quotes(chats)               # AI 분석용 (전체)

    # AI 분석: 캐시 확인
    cached = get_learning_report(user_id)
    if cached and not regenerate:
        ai_pattern   = cached["ai_pattern"]
        ai_advice    = cached["ai_advice"]
        ai_generated = cached["generated_at"][:16]
        ai_is_cached = True
    else:
        data_section = _build_data_section(stats, concepts, quotes_all, notebooks)
        ai_pattern, ai_advice = _call_gemini(data_section)
        save_learning_report(user_id, ai_pattern, ai_advice)
        ai_generated = datetime.now().strftime("%Y-%m-%d %H:%M")
        ai_is_cached = False

    return {
        "has_data":     True,
        "generated_at": datetime.now().strftime("%Y년 %m월 %d일"),
        "ai_generated": ai_generated,
        "ai_is_cached": ai_is_cached,
        "stats":        stats,
        "concepts":     concepts,
        "quotes":       quotes_display,
        "ai_pattern":   ai_pattern,
        "ai_advice":    ai_advice,
    }
