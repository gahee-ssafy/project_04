"""학습일지 보고서 API"""
from fastapi import APIRouter, Depends
from dependencies import get_current_user
from services.report import generate_report

router = APIRouter()


@router.get("")
def get_report(user=Depends(get_current_user)):
    """캐시된 AI 분석 포함 통합 보고서"""
    return generate_report(user["id"], regenerate=False)


@router.post("/regenerate")
def regenerate_report(user=Depends(get_current_user)):
    """AI 분석 재생성 후 저장"""
    return generate_report(user["id"], regenerate=True)
