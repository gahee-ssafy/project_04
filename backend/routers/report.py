"""학습일지 보고서 API"""
from fastapi import APIRouter, Depends
from dependencies import get_current_user
from services.report import generate_report

router = APIRouter()


@router.get("")
def get_report(user=Depends(get_current_user)):
    return generate_report(user["id"])
