import base64
from fastapi import APIRouter, Depends
from database import (
    get_sessions_with_memo,
    save_memo,
    add_to_notebook,
    update_notebook_entry,
    delete_notebook_entry,
)
from dependencies import get_current_user
from schemas.memo import MemoSaveRequest, NotebookAddRequest, NotebookUpdateRequest

router = APIRouter()


@router.get("/", summary="오답노트 목록")
def list_notebook(user=Depends(get_current_user)):
    return get_sessions_with_memo(user["id"])


@router.post("/", summary="오답노트 직접 추가")
def add_notebook(req: NotebookAddRequest, user=Depends(get_current_user)):
    img_bytes = base64.b64decode(req.image_data) if req.image_data else None
    session_id = add_to_notebook(
        user["id"],
        req.question,
        answer=req.answer or "",
        memo=req.memo or "",
        image_data=img_bytes,
        image_mime=req.image_mime,
    )
    return {"session_id": session_id, "message": "오답노트에 추가됐어요!"}


@router.put("/{session_id}/memo", summary="메모 저장")
def update_memo(session_id: int, req: MemoSaveRequest, user=Depends(get_current_user)):
    save_memo(user["id"], session_id, req.memo)
    return {"message": "저장됐어요!"}


@router.put("/{session_id}", summary="오답노트 항목 수정 (직접 추가 항목만)")
def update_notebook(session_id: int, req: NotebookUpdateRequest, user=Depends(get_current_user)):
    update_notebook_entry(session_id, user["id"], req.question, req.answer or "")
    return {"message": "수정됐어요!"}


@router.delete("/{session_id}", summary="오답노트 항목 삭제")
def delete_notebook(session_id: int, user=Depends(get_current_user)):
    delete_notebook_entry(session_id, user["id"])
    return {"message": "삭제됐어요!"}
