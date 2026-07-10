import json
import base64
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from database import get_all_problems, save_session, get_notebook_chat, save_notebook_chat, deduct_credits, get_credits
from dependencies import get_current_user
from schemas.session import AskRequest
from services.ai import ask, notebook_chat, notebook_chat_stream

router = APIRouter()


@router.post("/ask", summary="자유 질문 (AI 풀이 생성)")
def ask_question(req: AskRequest, user=Depends(get_current_user)):
    if not deduct_credits(user["id"], 1, "AI 질문"):
        raise HTTPException(status_code=402, detail="크레딧이 부족해요. 관리자에게 충전을 요청하세요.")
    img_bytes = base64.b64decode(req.image_data) if req.image_data else None
    answer = ask(
        req.query,
        image_bytes=img_bytes,
        image_mime=req.image_mime,
        chat_history=req.chat_history,
    )
    session_id = save_session(user["id"], req.query, answer, img_bytes, req.image_mime)
    return {"answer": answer, "session_id": session_id, "credits_remaining": get_credits(user["id"])}


class NotebookChatRequest(BaseModel):
    session_id: int
    question: str
    memo: str = ""
    solution: str = ""
    user_message: str = ""  # 비어있으면 opener 요청
    image_data: str = ""    # base64 필기 이미지 (선택)
    image_mime: str = "image/png"
    mode: str = "teacher"   # "teacher" | "student"


@router.get("/notebook-chat/{session_id}", summary="오답노트 채팅 기록 불러오기")
def get_chat(session_id: int, mode: str = "teacher", user=Depends(get_current_user)):
    history = get_notebook_chat(user["id"], session_id, mode)
    return {"history": history}


@router.post("/notebook-chat", summary="오답노트 메모 기반 AI 토론")
def notebook_chat_api(req: NotebookChatRequest, user=Depends(get_current_user)):
    history = get_notebook_chat(user["id"], req.session_id, req.mode)

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

    save_notebook_chat(user["id"], req.session_id, history, req.mode)
    return {"reply": reply, "history": history}


@router.post("/notebook-chat/stream", summary="오답노트 채팅 스트리밍")
def notebook_chat_stream_api(req: NotebookChatRequest, user=Depends(get_current_user)):
    history = get_notebook_chat(user["id"], req.session_id, req.mode)
    img_bytes = base64.b64decode(req.image_data) if req.image_data else None

    # opener는 규칙 기반이라 크레딧 차감 제외
    is_opener = not history and not req.user_message and not img_bytes
    if not is_opener:
        if not deduct_credits(user["id"], 1, "AI 토론"):
            raise HTTPException(status_code=402, detail="크레딧이 부족해요. 관리자에게 충전을 요청하세요.")

    def generate():
        full_reply = ""
        is_opener = not history and not req.user_message and not img_bytes

        for text in notebook_chat_stream(
            req.question, req.memo, req.solution, history,
            user_message=req.user_message,
            image_bytes=img_bytes, image_mime=req.image_mime or "image/png",
            mode=req.mode,
        ):
            full_reply += text
            yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"

        # history 저장
        new_history = list(history)
        if is_opener:
            new_history.append({"role": "assistant", "content": full_reply})
        else:
            if req.user_message or img_bytes:
                new_history.append({"role": "user", "content": req.user_message or "(필기 전송)", "has_image": bool(img_bytes)})
            new_history.append({"role": "assistant", "content": full_reply})

        save_notebook_chat(user["id"], req.session_id, new_history, req.mode)
        credits_left = get_credits(user["id"])
        yield f"data: {json.dumps({'done': True, 'history': new_history, 'credits_remaining': credits_left}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/solution/{problem_id}", summary="문제 풀이 조회 (미리 생성된 풀이)")
def get_solution(problem_id: int, user=Depends(get_current_user)):
    problems = {p["id"]: p for p in get_all_problems()}
    problem = problems.get(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없어요.")
    if not problem.get("solution"):
        raise HTTPException(status_code=404, detail="아직 풀이가 생성되지 않았어요.")
    return {"problem_id": problem_id, "solution": problem["solution"]}
