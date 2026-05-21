import base64
from fastapi import APIRouter, Depends, HTTPException
from database import get_all_problems, save_session
from dependencies import get_current_user
from schemas.session import AskRequest
from services.ai import ask

router = APIRouter()


@router.post("/ask", summary="자유 질문 (AI 풀이 생성)")
def ask_question(req: AskRequest, user=Depends(get_current_user)):
    img_bytes = base64.b64decode(req.image_data) if req.image_data else None
    answer = ask(
        req.query,
        image_bytes=img_bytes,
        image_mime=req.image_mime,
        chat_history=req.chat_history,
    )
    session_id = save_session(user["id"], req.query, answer, img_bytes, req.image_mime)
    return {"answer": answer, "session_id": session_id}


@router.get("/solution/{problem_id}", summary="문제 풀이 조회 (미리 생성된 풀이)")
def get_solution(problem_id: int, user=Depends(get_current_user)):
    problems = {p["id"]: p for p in get_all_problems()}
    problem = problems.get(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없어요.")
    if not problem.get("solution"):
        raise HTTPException(status_code=404, detail="아직 풀이가 생성되지 않았어요.")
    return {"problem_id": problem_id, "solution": problem["solution"]}
