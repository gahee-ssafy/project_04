from pydantic import BaseModel
from typing import Optional


class ExamRoundInfo(BaseModel):
    exam_year: int
    exam_round: int
    problem_count: int


class ProblemResponse(BaseModel):
    id: int
    topic: str
    question: str
    difficulty: str
    image_data: Optional[str]          # base64
    image_mime: Optional[str]
    exam_year: Optional[int]
    exam_round: Optional[int]


class ExamAnswerItem(BaseModel):
    problem_id: int
    user_answer: str
    is_correct: bool                   # 자기 채점


class ExamSubmitRequest(BaseModel):
    exam_year: int
    exam_round: int
    answers: list[ExamAnswerItem]


class ExamResultItem(BaseModel):
    problem_id: int
    question: str
    user_answer: str
    is_correct: bool
    solution: Optional[str]
    session_id: Optional[int]          # 오답노트에 생성된 session_id (오답일 때)
