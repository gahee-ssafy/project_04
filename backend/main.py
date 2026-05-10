# =============================================================
# main.py - FastAPI 애플리케이션 진입점
# 서버 설정, CORS, 라우터 등록, DB 초기화를 담당합니다.
# =============================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import search
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------------------
# lifespan: 서버 시작/종료 시 실행할 이벤트 핸들러
# @asynccontextmanager를 사용해 DB 초기화를 서버 시작 시점에 수행
# -------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 DB 테이블 자동 생성
    await init_db()
    print("✅ Database initialized")
    yield
    # 서버 종료 시 정리 작업 (필요 시 추가)
    print("🛑 Server shutting down")


# -------------------------------------------------------------
# FastAPI 앱 인스턴스 생성
# -------------------------------------------------------------
app = FastAPI(
    title="AI Search Engine",
    description="Perplexity 스타일의 AI 기반 검색 엔진 MVP",
    version="0.1.0",
    lifespan=lifespan,
)


# -------------------------------------------------------------
# CORS 설정
# React 개발 서버(localhost:3000)에서의 요청을 허용
# 프로덕션 배포 시 origins 목록을 실제 도메인으로 제한할 것
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# 라우터 등록
# 검색 관련 엔드포인트는 routers/search.py에서 관리
# -------------------------------------------------------------
app.include_router(search.router, prefix="/api/v1", tags=["search"])


# -------------------------------------------------------------
# 헬스체크 엔드포인트 - 서버 상태 확인용
# -------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "AI Search Engine is running 🚀"}


# -------------------------------------------------------------
# 로컬 개발 서버 실행 진입점
# 터미널에서 `python main.py` 또는 `uvicorn main:app --reload`
# -------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)