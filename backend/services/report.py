"""
학습일지 보고서 생성 서비스
AI 미사용 — 통계 + 경제학 개념 사전 매칭 + 조건부 템플릿 문장으로 구성
"""
import re
import json
from collections import Counter
from datetime import datetime, timezone

from database import get_conn

# ─── 경제학 개념 사전 ────────────────────────────────────────────
# { 표시 이름: [매칭할 키워드 목록] }
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
    "필립스곡선": ["필립스곡선", "필립스 곡선", "실업률과 인플레"],
    "케인즈": ["케인즈", "케인지안", "유효수요", "절약의 역설"],
    "승수효과": ["승수효과", "지출승수", "세금승수", "균형재정승수"],
    "최저임금·가격규제": ["최저임금", "최고가격", "가격하한", "가격상한"],
}

# ─── 불용어 ──────────────────────────────────────────────────────
STOPWORDS = {
    "이", "가", "을", "를", "은", "는", "의", "에", "도", "로", "으로",
    "이다", "있다", "없다", "하다", "되다", "같다", "보다",
    "그런데", "그리고", "그래서", "하지만", "왜냐하면",
    "문제", "내용", "경우", "설명", "이유", "때문", "부분", "개념",
    "관련", "통해", "따라", "위해", "대한", "대해", "것이", "것은", "것을",
    "어떻게", "왜", "무엇", "어떤", "얼마나",
}


# ─── DB 조회 ─────────────────────────────────────────────────────
def _get_raw_data(user_id: int) -> dict:
    conn = get_conn()

    # 오답노트 항목 (오답노트 + 모의고사)
    notebook_rows = conn.execute(
        """SELECT s.id, s.question, s.created_at, COALESCE(m.memo, '') AS memo
           FROM sessions s
           LEFT JOIN memos m ON m.session_id = s.id AND m.user_id = s.user_id
           WHERE s.user_id = ?
             AND (s.question LIKE '[오답노트]%' OR s.question LIKE '[모의고사]%')
           ORDER BY s.created_at ASC""",
        (user_id,),
    ).fetchall()

    # AI 채팅 내역
    chat_rows = conn.execute(
        """SELECT notebook_session_id, messages
           FROM notebook_chats
           WHERE user_id = ?""",
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


# ─── 통계 계산 ───────────────────────────────────────────────────
def _calc_stats(notebooks: list, chats_by_session: dict) -> dict:
    total = len(notebooks)
    if total == 0:
        return {"total": 0}

    memo_count = sum(1 for n in notebooks if n["memo"].strip())
    chat_sessions = sum(1 for n in notebooks if n["id"] in chats_by_session)

    # 학생이 보낸 메시지 수 (role == "user", opener 이후)
    student_msg_count = 0
    for msgs in chats_by_session.values():
        student_msg_count += sum(1 for m in msgs if m.get("role") == "user")

    # 활동 기간
    dates = [n["created_at"][:10] for n in notebooks if n.get("created_at")]
    first_date = min(dates) if dates else None
    last_date = max(dates) if dates else None
    active_days = len(set(dates))

    return {
        "total": total,
        "memo_count": memo_count,
        "memo_rate": round(memo_count / total * 100) if total else 0,
        "chat_sessions": chat_sessions,
        "chat_rate": round(chat_sessions / total * 100) if total else 0,
        "student_msg_count": student_msg_count,
        "first_date": first_date,
        "last_date": last_date,
        "active_days": active_days,
    }


# ─── 텍스트 수집 ─────────────────────────────────────────────────
def _collect_text(notebooks: list, chats_by_session: dict) -> str:
    parts = []
    for n in notebooks:
        if n["memo"].strip():
            parts.append(n["memo"])
    for msgs in chats_by_session.values():
        for m in msgs:
            if m.get("role") == "user":
                parts.append(m["content"])
    return " ".join(parts)


# ─── 경제학 개념 매칭 ────────────────────────────────────────────
def _extract_concepts(text: str) -> list[tuple[str, int]]:
    """개념 사전과 매칭해 (개념명, 등장 횟수) 리스트 반환 (빈도순)."""
    counts = Counter()
    for concept, keywords in ECON_CONCEPTS.items():
        for kw in keywords:
            counts[concept] += text.count(kw)
    # 1회 이상만
    result = [(c, n) for c, n in counts.items() if n > 0]
    result.sort(key=lambda x: -x[1])
    return result[:6]  # 상위 6개


# ─── 학생 직접 질문 추출 ─────────────────────────────────────────
def _extract_student_quotes(chats_by_session: dict) -> list[str]:
    quotes = []
    for msgs in chats_by_session.values():
        for m in msgs:
            if m.get("role") == "user":
                text = m["content"].strip()
                # 너무 짧은 건 제외 (단순 "네", "아니요" 등)
                if len(text) >= 10:
                    quotes.append(text)
    # 중복 제거 후 최대 5개
    seen = set()
    result = []
    for q in quotes:
        if q not in seen:
            seen.add(q)
            result.append(q)
        if len(result) >= 5:
            break
    return result


# ─── 템플릿 문장 생성 ────────────────────────────────────────────
def _build_overview(stats: dict) -> str:
    total = stats["total"]
    memo_rate = stats["memo_rate"]
    chat_sessions = stats["chat_sessions"]
    active_days = stats["active_days"]
    first = stats.get("first_date", "")
    last = stats.get("last_date", "")

    lines = []

    # 전체 문항 수
    if total == 0:
        return "아직 오답노트에 기록된 문제가 없어요."
    elif total < 5:
        lines.append(f"총 **{total}개**의 문제를 오답노트에 담았어요. 시작이 반이에요! 💪")
    elif total < 15:
        lines.append(f"총 **{total}개**의 오답 문제를 기록했어요.")
    else:
        lines.append(f"총 **{total}개**의 오답 문제를 꾸준히 모았어요. 성실한 학습 태도네요! 📚")

    # 메모율
    if memo_rate >= 70:
        lines.append(f"문제의 **{memo_rate}%**에 직접 메모를 남겼어요. 꼼꼼한 복습 습관이 잘 잡혀 있네요.")
    elif memo_rate >= 40:
        lines.append(f"문제의 **{memo_rate}%**에 메모를 작성했어요. 조금 더 채워가면 좋을 것 같아요.")
    elif memo_rate > 0:
        lines.append(f"아직 메모가 **{stats['memo_count']}개**밖에 없어요. 틀린 이유를 한 줄이라도 적어보세요.")
    else:
        lines.append("아직 메모를 한 개도 작성하지 않았어요. 메모가 복습의 핵심이에요!")

    # AI 토론
    if chat_sessions == 0:
        lines.append("아직 AI 토론은 활용하지 않았어요.")
    elif chat_sessions <= 2:
        lines.append(f"**{chat_sessions}개** 문제에서 AI와 토론했어요.")
    else:
        lines.append(f"**{chat_sessions}개** 문제에서 AI와 토론했어요. 적극적으로 활용하고 있네요! 🎯")

    # 활동 기간
    if first and last and first != last:
        lines.append(f"첫 기록은 **{first}**, 가장 최근은 **{last}** — **{active_days}일**에 걸쳐 학습했어요.")
    elif active_days == 1:
        lines.append(f"오늘 하루 집중적으로 기록했어요.")

    return "\n\n".join(lines)


def _build_advice(stats: dict, concepts: list) -> str:
    total = stats["total"]
    memo_rate = stats["memo_rate"]
    chat_sessions = stats["chat_sessions"]

    tips = []

    if memo_rate < 30:
        tips.append("틀린 문제마다 메모 한 줄을 목표로 해보세요. '왜 틀렸는지' 한 문장만으로도 충분해요.")

    if chat_sessions == 0 and total >= 3:
        tips.append("AI 토론 기능을 아직 써보지 않았어요. 어려운 문제 하나를 골라 AI와 대화해보세요. 이해가 훨씬 빨라져요.")

    if concepts:
        top = concepts[0][0]
        tips.append(f"**{top}** 관련 내용이 가장 자주 등장했어요. 해당 개념을 집중적으로 복습해보세요.")

    if memo_rate >= 70 and chat_sessions >= 3:
        tips.append("메모도 꾸준히 하고 AI 토론도 잘 활용하고 있어요. 이 페이스를 유지하면서 틀린 문제를 주기적으로 다시 풀어보세요.")

    if not tips:
        tips.append("꾸준히 오답노트를 관리하는 것 자체가 훌륭한 학습 전략이에요. 지금처럼 계속해봐요!")

    return "\n\n".join(tips)


# ─── 메인 함수 ───────────────────────────────────────────────────
def generate_report(user_id: int) -> dict:
    """학습일지 보고서 생성. 섹션별 딕셔너리 반환."""
    raw = _get_raw_data(user_id)
    notebooks = raw["notebooks"]
    chats_by_session = raw["chats_by_session"]

    if not notebooks:
        return {
            "has_data": False,
            "message": "아직 오답노트에 기록된 문제가 없어요. 모의고사를 풀고 틀린 문제를 추가해보세요!",
        }

    stats = _calc_stats(notebooks, chats_by_session)
    all_text = _collect_text(notebooks, chats_by_session)
    concepts = _extract_concepts(all_text)
    quotes = _extract_student_quotes(chats_by_session)

    return {
        "has_data": True,
        "generated_at": datetime.now().strftime("%Y년 %m월 %d일"),
        "stats": stats,
        "overview": _build_overview(stats),
        "concepts": concepts,          # [(이름, 횟수), ...]
        "quotes": quotes,              # [문장, ...]
        "advice": _build_advice(stats, concepts),
    }
