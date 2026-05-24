"""OX 복습 퀴즈 API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from dependencies import get_current_user
from services.quiz import generate_quiz, get_related_problem

router = APIRouter()


@router.get("")
def get_quiz(user=Depends(get_current_user)):
    """오답노트 풀이 기반 OX 퀴즈 생성"""
    return generate_quiz(user["id"])


class RelatedRequest(BaseModel):
    text: str


@router.post("/related")
def related_problem(req: RelatedRequest, user=Depends(get_current_user)):
    """틀린 OX 문제 텍스트 → 관련 기출문제"""
    result = get_related_problem(req.text)
    return result or {}
