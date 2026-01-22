"""
FastAPI 依賴注入
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from app.services.auth_service import AuthService
from app.models.schemas import UserInDB
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

# OAuth2 設定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# 創建全域 AuthService 實例（用於依賴注入）
_auth_service_instance = None

def get_auth_service() -> AuthService:
    """取得 AuthService 實例（單例模式）"""
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserInDB:
    """取得當前使用者（從 Token）"""
    return auth_service.get_current_user_from_token(token)


def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """取得當前活躍使用者"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="使用者帳號已停用")
    return current_user


def require_admin(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """要求管理員權限"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return current_user
