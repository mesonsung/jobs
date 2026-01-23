"""
認證相關 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.services.auth_service import AuthService
from app.models.schemas import User, UserCreate, Token, UserInDB
from app.api.dependencies import get_current_active_user, get_auth_service
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from typing import Annotated

router = APIRouter(prefix="/api/auth", tags=["認證"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """註冊報班帳號新使用者"""
    try:
        user = auth_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"註冊報班帳號失敗：{str(e)}")


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """使用者登入"""
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="使用者名稱或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
def get_current_user_info(
    current_user: UserInDB = Depends(get_current_active_user)
):
    """取得當前使用者資訊"""
    return User(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        address=current_user.address,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        line_user_id=current_user.line_user_id
    )
