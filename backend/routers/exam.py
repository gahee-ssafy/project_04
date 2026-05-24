from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import (
    get_exam_rounds,
    get_problems_by_round,
    save_exam_attempt,
    auto_add_wrong_to_notebook,
    get_all_problems,
)
from dependencies import get_current_user
from schemas.exam import ExamSubmitRequest, ExamResultItem

router = APIRouter()


@router.get("/rounds", summary="모의고사 회차 목록")
def list_rounds(user=Depends(get_current_user)):
    return get_exam_rounds()


@router.get("/rounds/{exam_year}/{exam_round}", summary="특정 회차 문제 목록")
def get_round_problems(exam_year: int, exam_round: int, user=Depends(get_current_user)):
    problems = get_problems_by_round(exam_year, exam_round)
    if not problems:
        raise HTTPException(status_code=404, detail="해당 회차의 문제가 없어요.")
    return [{k: v for k, v in p.items() if k != "solution"} for p in problems]


@router.post("/submit", summary="모의고사 제출 + 채점 (오답노트 자동저장 없음)")
def submit_exam(req: ExamSubmitRequest, user=Depends(get_current_user)):
    all_problems = {p["id"]: p for p in get_problems_by_round(req.exam_year, req.exam_round)}

    results = []
    for ans in req.answers:
        problem = all_problems.get(ans.problem_id)
        if not problem:
            continue

        save_exam_attempt(
            user["id"],
            req.exam_year,
            req.exam_round,
            ans.problem_id,
            ans.user_answer,
            ans.is_correct,
        )

        results.append(ExamResultItem(
            problem_id=ans.problem_id,
            question=problem["question"],
            user_answer=ans.user_answer,
            is_correct=ans.is_correct,
            solution=problem.get("solution") if not ans.is_correct else None,
            session_id=None,
        ))

    correct = sum(1 for r in results if r.is_correct)
    return {
        "total": len(results),
        "correct": correct,
        "wrong": len(results) - correct,
        "results": [r.model_dump() for r in results],
    }


class AddToNotebookRequest(BaseModel):
    exam_year: int
    exam_round: int
    problem_ids: list[int]


@router.post("/add-to-notebook", summary="선택한 오답을 오답노트에 저장")
def add_to_notebook(req: AddToNotebookRequest, user=Depends(get_current_user)):
    all_problems = {p["id"]: p for p in get_problems_by_round(req.exam_year, req.exam_round)}
    saved = 0
    for pid in req.problem_ids:
        problem = all_problems.get(pid)
        if problem:
            auto_add_wrong_to_notebook(user["id"], problem, "")
            saved += 1
    return {"saved": saved}
