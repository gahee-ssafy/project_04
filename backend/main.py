import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import init_db
from routers import auth, sessions, memo, problems, exam, ai, report, quiz, admin
from scheduler import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    init_db()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    # 종료
    scheduler.shutdown()


app = FastAPI(
    title="AI 경제학 튜터 API",
    description="기출문제 기반 모의고사 + 오답노트 + AI 토론 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
_raw = os.getenv("ALLOWED_ORIGINS", "*")
_origins = [o.strip() for o in _raw.split(",")] if _raw != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router,      prefix="/auth",      tags=["인증"])
app.include_router(sessions.router,  prefix="/sessions",  tags=["히스토리"])
app.include_router(memo.router,      prefix="/notebook",  tags=["오답노트"])
app.include_router(problems.router,  prefix="/problems",  tags=["문제은행"])
app.include_router(exam.router,      prefix="/exam",      tags=["모의고사"])
app.include_router(ai.router,        prefix="/ai",        tags=["AI"])
app.include_router(report.router,    prefix="/report",    tags=["학습일지"])
app.include_router(quiz.router,      prefix="/quiz",      tags=["OX퀴즈"])
app.include_router(admin.router,     prefix="/admin",     tags=["관리자"])


@app.get("/health", tags=["헬스체크"])
def health():
    return {"status": "ok", "message": "AI 경제학 튜터 API 서버가 실행 중이에요!"}


# 프론트엔드 정적 파일 서빙 (빌드 결과물이 있을 때만)
_dist = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_dist, "index.html"))
