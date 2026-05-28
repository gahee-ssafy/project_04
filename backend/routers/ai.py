import base64
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import get_all_problems, save_session, get_notebook_chat, save_notebook_chat
from dependencies import get_current_user
from schemas.session import AskRequest
from services.ai import ask, notebook_chat

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


class NotebookChatRequest(BaseModel):
    session_id: int
    question: str
    memo: str = ""
    solution: str = ""
    user_message: str = ""  # 비어있으면 opener 요청
    image_data: str = ""    # base64 필기 이미지 (선택)
    image_mime: str = "image/png"


@router.get("/notebook-chat/{session_id}", summary="오답노트 채팅 기록 불러오기")
def get_chat(session_id: int, user=Depends(get_current_user)):
    history = get_notebook_chat(user["id"], session_id)
    return {"history": history}


@router.post("/notebook-chat", summary="오답노트 메모 기반 AI 토론")
def notebook_chat_api(req: NotebookChatRequest, user=Depends(get_current_user)):
    history = get_notebook_chat(user["id"], req.session_id)

    img_bytes = base64.b64decode(req.image_data) if req.image_data else None
    reply = notebook_chat(req.question, req.memo, req.solution, history,
                          image_bytes=img_bytes, image_mime=req.image_mime or "image/png")

    # 학생 메시지가 있으면 history에 추가 후 AI 응답도 저장
    if req.user_message or img_bytes:
        msg_content = req.user_message or "(필기 전송)"
        history.append({"role": "user", "content": msg_content, "has_image": bool(img_bytes)})
        history.append({"role": "assistant", "content": reply})
    else:
        # opener: AI 첫 메시지만 저장
        if not history:
            history.append({"role": "assistant", "content": reply})

    save_notebook_chat(user["id"], req.session_id, history)
    return {"reply": reply, "history": history}


@router.get("/solution/{problem_id}", summary="문제 풀이 조회 (미리 생성된 풀이)")
def get_solution(problem_id: int, user=Depends(get_current_user)):
    problems = {p["id"]: p for p in get_all_problems()}
    problem = problems.get(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없어요.")
    if not problem.get("solution"):
        raise HTTPException(status_code=404, detail="아직 풀이가 생성되지 않았어요.")
    return {"problem_id": problem_id, "solution": problem["solution"]}
