"""관리자 전용 API — 문제 생성 및 저장"""
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user
from database import get_conn, DB_PATH
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
    saved = 0
    for q in req.questions:
        # ①②③④ 선지를 question text에 합쳐서 저장
        choices_text = "\n".join(f"{k} {v}" for k, v in q.choices.items())
        full_question = f"{q.question}\n{choices_text}"

        conn.execute(
            """INSERT INTO problems
               (topic, question, difficulty, correct_answer, solution,
                exam_type, ncs_agency, ncs_domain, exam_year)
               VALUES (?, ?, ?, ?, ?, 'ncs', ?, ?, ?)""",
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
    conn.close()
    return {"saved": saved}


# ⚠️ 임시 엔드포인트 — DB 업로드 후 삭제할 것
@router.post("/upload-db", summary="DB 파일 업로드 (임시)")
async def upload_db(file: UploadFile = File(...), user=Depends(get_current_user)):
    secret = os.getenv("DB_UPLOAD_SECRET", "")
    if not secret:
        raise HTTPException(status_code=403, detail="DB_UPLOAD_SECRET 환경변수가 설정되지 않았습니다.")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"message": f"DB 업로드 완료: {DB_PATH}"}
