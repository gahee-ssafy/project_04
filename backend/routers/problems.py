from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database import get_all_problems, get_conn, update_problem_question_text
from dependencies import get_current_user
from services.report import extract_concept

router = APIRouter()


@router.get("/", summary="문제은행 전체 목록")
def list_problems(user=Depends(get_current_user)):
    problems = get_all_problems()
    # 풀이(solution)는 목록에서 제외 — 모의고사 중 노출 방지
    return [
        {k: v for k, v in p.items() if k != "solution"}
        for p in problems
    ]


class QuestionTextUpdate(BaseModel):
    question_text: str


@router.patch("/{problem_id}/question-text", summary="문제 질문 텍스트 업데이트 (관리자)")
def set_question_text(
    problem_id: int,
    body: QuestionTextUpdate,
    user=Depends(get_current_user),
):
    """이미지 기반 문제의 실제 질문 텍스트를 저장.
    저장 후 자동으로 concept 태그를 재추출한다."""
    from services.report import extract_concept
    from database import get_conn

    update_problem_question_text(problem_id, body.question_text)

    concept = extract_concept(body.question_text)
    if concept:
        conn = get_conn()
        conn.execute("UPDATE problems SET concept = ? WHERE id = ?", (concept, problem_id))
        conn.commit()
        conn.close()

    return {"ok": True, "concept": concept}
