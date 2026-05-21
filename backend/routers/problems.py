from fastapi import APIRouter, Depends, HTTPException
from database import get_all_problems
from dependencies import get_current_user

router = APIRouter()


@router.get("/", summary="문제은행 전체 목록")
def list_problems(user=Depends(get_current_user)):
    problems = get_all_problems()
    # 풀이(solution)는 목록에서 제외 — 모의고사 중 노출 방지
    return [
        {k: v for k, v in p.items() if k != "solution"}
        for p in problems
    ]
