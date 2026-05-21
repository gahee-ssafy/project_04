from fastapi import APIRouter, Depends, HTTPException
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
    # 풀이는 제출 전까지 숨김
    return [{k: v for k, v in p.items() if k != "solution"} for p in problems]


@router.post("/submit", summary="모의고사 제출 + 자동 채점 + 오답노트 이동")
def submit_exam(req: ExamSubmitRequest, user=Depends(get_current_user)):
    # 문제 정보 조회 (풀이 포함)
    all_problems = {p["id"]: p for p in get_problems_by_round(req.exam_year, req.exam_round)}

    results = []
    for ans in req.answers:
        problem = all_problems.get(ans.problem_id)
        if not problem:
            continue

        # 응시 기록 저장
        save_exam_attempt(
            user["id"],
            req.exam_year,
            req.exam_round,
            ans.problem_id,
            ans.user_answer,
            ans.is_correct,
        )

        session_id = None
        # 오답이면 자동으로 오답노트에 추가
        if not ans.is_correct:
            session_id = auto_add_wrong_to_notebook(user["id"], problem, ans.user_answer)

        results.append(ExamResultItem(
            problem_id=ans.problem_id,
            question=problem["question"],
            user_answer=ans.user_answer,
            is_correct=ans.is_correct,
            solution=problem.get("solution") if not ans.is_correct else None,
            session_id=session_id,
        ))

    correct = sum(1 for r in results if r.is_correct)
    return {
        "total": len(results),
        "correct": correct,
        "wrong": len(results) - correct,
        "results": [r.model_dump() for r in results],
    }
