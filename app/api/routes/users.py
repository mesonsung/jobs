"""
使用者管理相關 API 路由
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from app.services.auth_service import AuthService
from app.models.schemas import User, UserInDB
from app.api.dependencies import require_admin, get_auth_service
from app.core.database import SessionLocal
from app.core.time_utils import format_datetime_taiwan
from app.models.user import UserModel
from typing import Annotated

router = APIRouter(prefix="/api/users", tags=["使用者管理"])


@router.get("", response_model=List[User])
def get_all_users(
    current_user: Annotated[UserInDB, Depends(require_admin)]
):
    """取得所有使用者列表（需要管理員權限）"""
    db = SessionLocal()
    try:
        user_models = db.query(UserModel).order_by(UserModel.created_at.desc()).all()
        return [
            User(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                birthday=user.birthday,
                phone=user.phone,
                address=user.address,
                id_number=user.id_number,
                is_admin=user.is_admin,
                is_active=user.is_active,
                created_at=format_datetime_taiwan(user.created_at),
                line_user_id=user.line_user_id
            )
            for user in user_models
        ]
    finally:
        db.close()


@router.get("/{username}", response_model=User)
def get_user(
    username: str,
    current_user: Annotated[UserInDB, Depends(require_admin)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """取得特定使用者資訊（需要管理員權限）"""
    user = auth_service.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    return User(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        birthday=user.birthday,
        phone=user.phone,
        address=user.address,
        id_number=user.id_number,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        line_user_id=user.line_user_id
    )
