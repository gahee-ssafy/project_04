from fastapi import APIRouter, Depends
from database import get_sessions, get_sessions_last_week, get_user_summaries, save_user_summary, get_all_sessions_for_summary
from dependencies import get_current_user
from services.ai import summarize_history

router = APIRouter()


@router.get("/", summary="히스토리 목록 (최근 50개)")
def list_sessions(user=Depends(get_current_user)):
    sessions = get_sessions(user["id"])
    _SKIP = ("[심화학습]", "[유사문제]", "[토론]", "[오답노트]", "[모의고사]")
    return [s for s in sessions if not s["question"].startswith(_SKIP)]


@router.get("/last-week", summary="최근 7일 세션")
def last_week(user=Depends(get_current_user)):
    return get_sessions_last_week(user["id"])


@router.get("/summaries", summary="AI 학습 요약 목록")
def list_summaries(user=Depends(get_current_user)):
    return get_user_summaries(user["id"])


@router.post("/summaries", summary="AI 학습 요약 생성")
def create_summary(user=Depends(get_current_user)):
    all_sessions = get_all_sessions_for_summary(user["id"])
    summary = summarize_history(all_sessions)
    save_user_summary(user["id"], summary)
    return {"summary": summary}
