# =============================================================
# models.py - SQLModel 기반 데이터베이스 테이블 정의
# SQLite3와 연동되며, SQLAlchemy ORM을 SQLModel로 감싸 사용합니다.
# =============================================================

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# -------------------------------------------------------------
# SearchQuery - 사용자의 검색 쿼리 기록 테이블
# 검색어, 생성일, 응답 토큰 수 등을 저장합니다.
# -------------------------------------------------------------
class SearchQuery(SQLModel, table=True):
    __tablename__ = "search_queries"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 사용자가 입력한 검색어
    query: str = Field(index=True, max_length=1000)

    # 최종 AI 요약 응답 (스트리밍 완료 후 저장)
    answer: Optional[str] = Field(default=None)

    # 검색에 소요된 시간 (초)
    elapsed_seconds: Optional[float] = Field(default=None)

    # 레코드 생성 시각
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 이미지 바이트 데이터 (이미지 검색이면 저장, 텍스트 검색이면 None)
    image_data: Optional[bytes] = Field(default=None)

# -------------------------------------------------------------
# SearchSource - 검색 결과에서 참조한 출처(소스) 테이블
# 각 SearchQuery에 여러 소스가 연결됩니다. (1:N 관계)
# -------------------------------------------------------------
class SearchSource(SQLModel, table=True):
    __tablename__ = "search_sources"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 부모 쿼리 ID (외래 키)
    query_id: int = Field(foreign_key="search_queries.id", index=True)

    # 소스 제목 (웹페이지 타이틀)
    title: str = Field(max_length=500)

    # 소스 URL
    url: str = Field(max_length=2000)

    # 소스에서 추출한 핵심 스니펫 (RAG에 사용)
    snippet: Optional[str] = Field(default=None)

    # 소스 순위 (1이 가장 관련성 높음)
    rank: int = Field(default=1)


# -------------------------------------------------------------
# Pydantic 스키마 - API 요청/응답 유효성 검사용
# SQLModel 테이블과 별개로, 입출력 데이터 구조를 명확히 정의
# -------------------------------------------------------------

class SearchRequest(SQLModel):
    """POST /search 요청 바디"""
    query: str = Field(min_length=1, max_length=1000, description="검색할 질문")


class SourceOut(SQLModel):
    """응답에 포함될 소스 정보"""
    title: str
    url: str
    snippet: Optional[str] = None
    rank: int


class SearchHistoryOut(SQLModel):
    """검색 히스토리 응답 스키마"""
    id: int
    query: str
    answer: Optional[str]
    elapsed_seconds: Optional[float]
    created_at: datetime