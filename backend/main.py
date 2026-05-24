from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import auth, sessions, memo, problems, exam, ai, report

app = FastAPI(
    title="AI 경제학 튜터 API",
    description="기출문제 기반 모의고사 + 오답노트 + AI 토론 서비스",
    version="1.0.0",
)

# CORS — 개발 중 전체 허용 (배포 시 origins 제한 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 초기화 (앱 시작 시)
init_db()

# 라우터 등록
app.include_router(auth.router,      prefix="/auth",      tags=["인증"])
app.include_router(sessions.router,  prefix="/sessions",  tags=["히스토리"])
app.include_router(memo.router,      prefix="/notebook",  tags=["오답노트"])
app.include_router(problems.router,  prefix="/problems",  tags=["문제은행"])
app.include_router(exam.router,      prefix="/exam",      tags=["모의고사"])
app.include_router(ai.router,        prefix="/ai",        tags=["AI"])
app.include_router(report.router,    prefix="/report",    tags=["학습일지"])


@app.get("/", tags=["헬스체크"])
def root():
    return {"status": "ok", "message": "AI 경제학 튜터 API 서버가 실행 중이에요!"}
