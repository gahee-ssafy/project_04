import os
from fastapi import APIRouter, HTTPException, Depends
from schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from database import create_user, get_user_by_credentials, get_credits
from dependencies import create_access_token, get_current_user

router = APIRouter()


@router.post("/register", summary="회원가입")
def register(req: RegisterRequest):
    if os.getenv("ALLOW_REGISTER", "true").lower() != "true":
        raise HTTPException(status_code=403, detail="회원가입이 비활성화되어 있습니다.")
    if not create_user(req.username, req.password):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디예요.")
    return {"message": "회원가입 완료!"}


@router.post("/login", response_model=TokenResponse, summary="로그인")
def login(req: LoginRequest):
    user = get_user_by_credentials(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸어요.")
    token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}


@router.get("/me", summary="내 정보 조회")
def me(user=Depends(get_current_user)):
    return {"id": user["id"], "username": user["username"], "credits": get_credits(user["id"])}
