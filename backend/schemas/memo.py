from pydantic import BaseModel
from typing import Optional


class MemoSaveRequest(BaseModel):
    memo: str


class NotebookAddRequest(BaseModel):
    question: str
    answer: Optional[str] = ""
    memo: Optional[str] = ""
    image_data: Optional[str] = None   # base64
    image_mime: Optional[str] = None


class NotebookUpdateRequest(BaseModel):
    question: str
    answer: Optional[str] = ""
