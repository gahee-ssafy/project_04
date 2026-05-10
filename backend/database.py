# =============================================================
# database.py - SQLite3 데이터베이스 연결 및 세션 관리
# SQLModel + aiosqlite를 사용한 비동기 DB 처리
# =============================================================

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import os

# -------------------------------------------------------------
# DB 파일 경로 설정
# 환경변수 DB_PATH가 없으면 기본값으로 ./data/search.db 사용
# -------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "./data/search.db")

# data/ 디렉토리가 없으면 자동 생성
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# [질문] aiosqlite가 뭐예요? 
# aiosqlite를 사용한 비동기 SQLite 연결 URL
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# -------------------------------------------------------------
# 비동기 엔진 생성
# connect_args: SQLite 멀티스레드 허용 설정
# echo=True: SQL 쿼리 로깅 (개발 시 유용, 프로덕션에서는 False)
# -------------------------------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True,
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # commit 후에도 객체 속성 유지
)


# -------------------------------------------------------------
# init_db - 모든 SQLModel 테이블을 DB에 생성
# main.py의 lifespan에서 서버 시작 시 호출됨
# -------------------------------------------------------------
async def init_db():
    async with engine.begin() as conn:
        # models.py에서 정의한 모든 테이블을 자동 생성 (없으면 생성, 있으면 유지)
        await conn.run_sync(SQLModel.metadata.create_all)


# -------------------------------------------------------------
# get_session - FastAPI 의존성 주입용 세션 제공자
# 각 API 요청마다 새로운 DB 세션을 열고, 완료 시 자동으로 닫음
# 사용법: async def my_endpoint(session: AsyncSession = Depends(get_session))
# -------------------------------------------------------------
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session