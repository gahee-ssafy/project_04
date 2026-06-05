from pydantic import BaseModel
from typing import Optional


class AskRequest(BaseModel):
    query: str
    image_data: Optional[str] = None   # base64
    image_mime: Optional[str] = None
    chat_history: Optional[list] = []


class SessionResponse(BaseModel):
    id: int
    question: str
    answer: Optional[str]
    image_data: Optional[str]          # base64
    image_mime: Optional[str]
    created_at: str
