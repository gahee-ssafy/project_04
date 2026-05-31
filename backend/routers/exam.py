from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import (
    get_exam_rounds, get_ncs_list,
    get_problems_by_round, get_problems_by_ncs,
    save_exam_attempt, save_exam_attempt_ncs,
    auto_add_wrong_to_notebook,
)
from dependencies import get_current_user
from schemas.exam import ExamSubmitRequest, ExamResultItem

router = APIRouter()


# ── 목록 ────────────────────────────────────────────────────────
@router.get("/rounds", summary="공무원 기출 회차 목록")
def list_rounds(user=Depends(get_current_user)):
    return get_exam_rounds()


@router.get("/ncs", summary="NCS 문제 목록 (대행사/년도/분야)")
def list_ncs(user=Depends(get_current_user)):
    return get_ncs_list()


# ── 문제 조회 ────────────────────────────────────────────────────
@router.get("/rounds/{exam_year}/{exam_round}", summary="공무원 기출 문제 목록")
def get_round_problems(exam_year: int, exam_round: int, user=Depends(get_current_user)):
    problems = get_problems_by_round(exam_year, exam_round)
    if not problems:
        raise HTTPException(status_code=404, detail="해당 회차의 문제가 없어요.")
    return [{k: v for k, v in p.items() if k != "solution"} for p in problems]


@router.get("/ncs/{agency}/{exam_year}/{domain}", summary="NCS 문제 목록")
def get_ncs_problems(agency: str, exam_year: int, domain: str,
                     user=Depends(get_current_user)):
    from urllib.parse import unquote
    problems = get_problems_by_ncs(unquote(agency), exam_year, unquote(domain))
    if not problems:
        raise HTTPException(status_code=404, detail="해당 NCS 문제가 없어요.")
    return [{k: v for k, v in p.items() if k != "solution"} for p in problems]


# ── 제출 ────────────────────────────────────────────────────────
class NcsSubmitRequest(BaseModel):
    ncs_agency: str
    exam_year: int
    ncs_domain: str
    answers: list


@router.post("/submit", summary="공무원 기출 제출")
def submit_exam(req: ExamSubmitRequest, user=Depends(get_current_user)):
    all_problems = {p["id"]: p for p in get_problems_by_round(req.exam_year, req.exam_round)}
    return _build_result(all_problems, req.answers, user["id"],
                         lambda ans, prob: save_exam_attempt(
                             user["id"], req.exam_year, req.exam_round,
                             ans.problem_id, ans.user_answer, ans.is_correct))


@router.post("/ncs/submit", summary="NCS 제출")
def submit_ncs(req: NcsSubmitRequest, user=Depends(get_current_user)):
    from schemas.exam import ExamResultItem, AnswerItem
    answers = [AnswerItem(**a) if isinstance(a, dict) else a for a in req.answers]
    all_problems = {p["id"]: p for p in get_problems_by_ncs(
        req.ncs_agency, req.exam_year, req.ncs_domain)}
    return _build_result(all_problems, answers, user["id"],
                         lambda ans, prob: save_exam_attempt_ncs(
                             user["id"], req.ncs_agency, req.exam_year, req.ncs_domain,
                             ans.problem_id, ans.user_answer, ans.is_correct))


def _build_result(all_problems, answers, user_id, save_fn):
    from schemas.exam import ExamResultItem
    results = []
    for ans in answers:
        problem = all_problems.get(ans.problem_id)
        if not problem:
            continue
        save_fn(ans, problem)
        results.append(ExamResultItem(
            problem_id=ans.problem_id,
            question=problem["question"],
            user_answer=ans.user_answer,
            is_correct=ans.is_correct,
            solution=problem.get("solution") if not ans.is_correct else None,
            session_id=None,
        ))
    correct = sum(1 for r in results if r.is_correct)
    return {"total": len(results), "correct": correct,
            "wrong": len(results) - correct,
            "results": [r.model_dump() for r in results]}


# ── 오답노트 저장 ────────────────────────────────────────────────
class AddToNotebookRequest(BaseModel):
    exam_year: int
    exam_round: Optional[int] = None
    ncs_agency: Optional[str] = None
    ncs_domain: Optional[str] = None
    problem_ids: list[int]


@router.post("/add-to-notebook", summary="선택한 오답을 오답노트에 저장")
def add_to_notebook(req: AddToNotebookRequest, user=Depends(get_current_user)):
    if req.ncs_agency:
        all_problems = {p["id"]: p for p in get_problems_by_ncs(
            req.ncs_agency, req.exam_year, req.ncs_domain)}
    else:
        all_problems = {p["id"]: p for p in get_problems_by_round(
            req.exam_year, req.exam_round)}
    saved = 0
    for pid in req.problem_ids:
        problem = all_problems.get(pid)
        if problem:
            auto_add_wrong_to_notebook(user["id"], problem, "")
            saved += 1
    return {"saved": saved}
