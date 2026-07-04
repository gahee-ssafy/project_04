"""관리자 전용 API — 문제 생성 및 저장"""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from database import get_conn, _cursor, charge_credits, get_all_users_credits
from services.generate import generate_ncs_questions

router = APIRouter()


class GenerateRequest(BaseModel):
    agency: str
    exam_year: int
    domain: str
    sample_text: str   # 예시 문제 텍스트 (2~3개 붙여넣기)
    count: int = 5


class QuestionItem(BaseModel):
    question: str
    choices: dict      # {"①": "...", "②": "...", ...}
    answer: str        # "①" ~ "④"
    explanation: Optional[str] = ""


class SaveRequest(BaseModel):
    agency: str
    exam_year: int
    domain: str
    questions: list[QuestionItem]



class ChargeRequest(BaseModel):
    user_id: int
    amount: int
    reason: str = "관리자 충전"


@router.get("/credits", summary="전체 유저 크레딧 현황")
def list_credits(user=Depends(get_current_user)):
    return {"users": get_all_users_credits()}


@router.post("/credits/charge", summary="크레딧 충전")
def charge(req: ChargeRequest, user=Depends(get_current_user)):
    charge_credits(req.user_id, req.amount, req.reason)
    return {"message": f"{req.user_id}번 유저에게 {req.amount} 크레딧 충전 완료"}


@router.post("/generate", summary="NCS 문제 AI 생성")
def generate(req: GenerateRequest, user=Depends(get_current_user)):
    try:
        questions = generate_ncs_questions(
            domain=req.domain,
            agency=req.agency,
            sample_text=req.sample_text,
            count=req.count,
        )
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"생성 실패: {str(e)}")


@router.post("/save-ncs", summary="생성된 NCS 문제 저장")
def save_ncs(req: SaveRequest, user=Depends(get_current_user)):
    conn = get_conn()
    cur = _cursor(conn)
    saved = 0
    for q in req.questions:
        choices_text = "\n".join(f"{k} {v}" for k, v in q.choices.items())
        full_question = f"{q.question}\n{choices_text}"

        cur.execute(
            """INSERT INTO problems
               (topic, question, difficulty, correct_answer, solution,
                exam_type, ncs_agency, ncs_domain, exam_year)
               VALUES (%s, %s, %s, %s, %s, 'ncs', %s, %s, %s)""",
            (
                req.domain,
                full_question,
                "보통",
                q.answer,
                q.explanation or "",
                req.agency,
                req.domain,
                req.exam_year,
            ),
        )
        saved += 1
    conn.commit()
    cur.close()
    conn.close()
    return {"saved": saved}
