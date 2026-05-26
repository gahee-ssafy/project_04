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
    # ── 미시 기초 ──────────────────────────────────────────────────
    "수요·공급": ["수요곡선", "수요량", "수요의", "수요 증가", "수요 감소",
                  "공급곡선", "공급량", "공급의", "공급 증가", "공급 감소",
                  "균형가격", "균형거래량", "초과수요", "초과공급"],
    "탄력성": ["탄력성", "탄력적", "비탄력", "가격탄력", "소득탄력", "교차탄력"],
    "소비자이론": ["한계대체율", "MRS", "무차별곡선", "예산제약", "효용극대화",
                   "소비자잉여", "효용함수", "가격효과", "소득효과", "대체효과",
                   "강단조성", "단조성", "보상변화", "대등변화", "현시선호", "추가 소득"],
    "생산자이론": ["생산함수", "한계비용", "평균비용", "등량곡선", "등비용선",
                   "MRTS", "생산자잉여", "규모의 경제", "규모수익", "손익분기",
                   "한계생산", "MP_L", "MP_K", "오일러", "요소소득", "비용 제약"],
    "시장구조": ["완전경쟁", "독점적 경쟁", "독점", "과점", "가격차별",
                 "이윤극대화", "MR", "MC", "한계수입", "시장지배력"],
    "시장실패": ["시장실패", "외부효과", "공공재", "정보비대칭", "역선택", "도덕적 해이",
                 "보조금"],
    "후생경제학": ["사회후생", "파레토", "칼도힉스", "사회후생함수", "배분 효율"],
    "게임이론": ["게임이론", "내쉬균형", "우월전략", "죄수의 딜레마", "혼합전략",
                 "순수전략", "용의자", "보수행렬", "무차별해지", "최적반응"],
    "소득분배": ["지니계수", "로렌츠", "5분위", "10분위", "소득불평등", "빈곤율",
                 "균등분배대등소득", "앳킨슨"],
    "기대효용·위험": ["기대효용", "확실성등가", "위험기피", "위험프리미엄",
                      "기대값", "위험중립", "위험선호"],
    "채권·금융": ["채권", "이자수익", "자본손실", "채권수익률", "레버리지", "수익률"],
    "최저임금·가격규제": ["최저임금", "최고가격", "가격하한", "가격상한"],
    "조세귀착": ["조세귀착", "조세부담", "경제적 순손실", "자중손실", "DWL"],

    # ── 거시 기초 ──────────────────────────────────────────────────
    "GDP·국민소득": ["GDP", "국내총생산", "국민소득", "GNP", "명목GDP", "실질GDP",
                     "국민총소득", "경제성장률"],
    "소비·저축": ["소비함수", "한계소비성향", "MPC", "저축률", "가처분소득", "절약의 역설"],
    "투자": ["투자함수", "한계효율", "투자승수", "가속도원리", "토빈"],
    "승수효과": ["승수효과", "지출승수", "세금승수", "균형재정승수", "재정승수"],
    "IS-LM": ["IS곡선", "LM곡선", "IS-LM", "유동성함정", "구축효과",
               "$IS$", "$LM$", "IS 곡선", "LM 곡선", "IS곡선", "LM곡선"],
    "총수요·총공급": ["총수요", "총공급", "AD곡선", "AS곡선", "AD-AS"],
    "케인즈": ["케인즈", "케인지안", "유효수요"],
    "물가·인플레이션": ["물가", "인플레이션", "인플레", "CPI", "디플레이션",
                        "스태그플레이션", "물가상승률"],
    "필립스곡선": ["필립스곡선", "필립스 곡선", "자연실업률", "기대인플레"],
    "노동시장": ["실업률", "구직률", "실직률", "자연실업률", "마찰적 실업",
                 "구조적 실업", "경기적 실업", "노동수요", "노동공급", "임금"],
    "경제성장": ["솔로모형", "황금률", "저축률", "수렴가설", "내생적 성장",
                 "자본축적", "1인당 자본", "균제상태"],
    "금리·이자율": ["금리", "이자율", "기준금리", "실질금리", "명목금리", "피셔방정식"],
    "재정정책": ["재정정책", "정부지출", "조세", "국채", "집행시차", "내부시차", "외부시차"],
    "통화정책": ["통화정책", "통화량", "본원통화", "통화승수", "공개시장조작", "지급준비율"],

    # ── 국제경제 ───────────────────────────────────────────────────
    "환율": ["환율", "절상", "절하", "평가절상", "평가절하", "구매력평가",
             "이자율평형", "J커브"],
    "무역·국제수지": ["경상수지", "무역수지", "자본수지", "수출입", "국제수지"],
    "비교우위": ["비교우위", "절대우위", "특화", "기회비용", "헥셔", "오린"],
}

# ─── 개념 태그 추출 (외부에서도 import 가능) ─────────────────────
def extract_concept(text: str) -> str | None:
    """해설·질문 텍스트에서 ECON_CONCEPTS 매칭 → 가장 많이 등장한 개념 반환."""
    from collections import Counter
    counts = Counter()
    for concept, keywords in ECON_CONCEPTS.items():
        for kw in keywords:
            counts[concept] += text.count(kw)
    hits = [(c, n) for c, n in counts.items() if n > 0]
    if not hits:
        return None
    return max(hits, key=lambda x: x[1])[0]


# ─── DB 조회 ─────────────────────────────────────────────────────
def _get_raw_data(user_id: int) -> dict:
    conn = get_conn()
    notebook_rows = conn.execute(
        """SELECT s.id, s.question, s.created_at,
                  COALESCE(m.memo, '') AS memo,
                  COALESCE(p.concept, '') AS problem_concept
           FROM sessions s
           LEFT JOIN memos m ON m.session_id = s.id AND m.user_id = s.user_id
           LEFT JOIN problems p ON p.id = s.problem_id
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
    # 학생 직접 작성 메모
    parts = [n["memo"] for n in notebooks if n["memo"].strip()]
    # AI 토론에서 학생 발화
    for msgs in chats_by_session.values():
        parts += [m["content"] for m in msgs if m.get("role") == "user"]
    return " ".join(parts)


# ─── 개념 추출 ───────────────────────────────────────────────────
def _extract_concepts(notebooks: list, chats_by_session: dict = None) -> list[tuple[str, int]]:
    counts = Counter()
    chats_by_session = chats_by_session or {}

    for n in notebooks:
        concept = n.get("problem_concept", "")

        # 개념 태그가 없는 항목(직접 추가 등)은 메모/질문 텍스트로 보완
        if not concept:
            combined = f"{n.get('question', '')} {n.get('memo', '')}"
            best, best_n = None, 0
            for c, keywords in ECON_CONCEPTS.items():
                cnt = sum(combined.count(kw) for kw in keywords)
                if cnt > best_n:
                    best, best_n = c, cnt
            concept = best

        if not concept:
            continue

        # ① 오답노트에 있음 → +1
        counts[concept] += 1

        # ② 메모 작성 → +1 (길이 무관)
        if n.get("memo", "").strip():
            counts[concept] += 1

        # ③ AI 토론 → 학생 메시지 수만큼 추가
        session_msgs = chats_by_session.get(n["id"], [])
        user_msg_count = sum(1 for m in session_msgs if m.get("role") == "user")
        counts[concept] += user_msg_count

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
    concepts       = _extract_concepts(notebooks, chats)
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
