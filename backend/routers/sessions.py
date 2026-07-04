from fastapi import APIRouter, Depends
from database import get_sessions, get_sessions_last_week, get_all_sessions_for_summary
from dependencies import get_current_user

router = APIRouter()


@router.get("/", summary="히스토리 목록 (최근 50개)")
def list_sessions(user=Depends(get_current_user)):
    sessions = get_sessions(user["id"])
    _SKIP = ("[심화학습]", "[유사문제]", "[토론]", "[오답노트]", "[모의고사]")
    return [s for s in sessions if not s["question"].startswith(_SKIP)]


@router.get("/last-week", summary="최근 7일 세션")
def last_week(user=Depends(get_current_user)):
    return get_sessions_last_week(user["id"])


