"""
認證服務
"""
import os
import datetime
from typing import Optional
from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.database import SessionLocal
from app.core.logger import setup_logger
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.models.user import UserModel
from app.models.schemas import User, UserInDB, UserCreate, TokenData
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ADMIN_USERNAME, ADMIN_PASSWORD

# 設置 logger
logger = setup_logger(__name__)


class AuthService:
    """認證服務"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化認證服務
        
        參數:
            db: 資料庫會話（可選，如果提供則使用，否則創建新會話）
        """
        self.db = db
        self._create_default_admin()
    
    def _get_db(self) -> Session:
        """取得資料庫會話"""
        if self.db:
            return self.db
        return SessionLocal()
    
    def _create_default_admin(self):
        """建立預設管理員帳號"""
        db = self._get_db()
        try:
            default_admin_username = ADMIN_USERNAME
            default_admin_password = ADMIN_PASSWORD
            
            # bcrypt 限制密碼不能超過 72 字節，如果超過則截斷
            if len(default_admin_password.encode('utf-8')) > 72:
                default_admin_password = default_admin_password[:72]
                logger.warning("管理員密碼超過 72 字節，已自動截斷")
            
            # 檢查是否已存在
            existing_user = db.query(UserModel).filter(UserModel.username == default_admin_username).first()
            if not existing_user:
                admin_user = UserModel(
                    id="USER-ADMIN-001",
                    username=default_admin_username,
                    email="admin@example.com",
                    full_name="系統管理員",
                    is_admin=True,
                    is_active=True,
                    hashed_password=get_password_hash(default_admin_password)
                )
                db.add(admin_user)
                db.commit()
                logger.info(f"已建立預設管理員帳號：{default_admin_username}")
        except Exception as e:
            db.rollback()
            logger.warning(f"建立預設管理員帳號失敗：{e}", exc_info=True)
        finally:
            if not self.db:
                db.close()
    
    def _get_next_user_id(self, db: Optional[Session] = None) -> str:
        """取得下一個使用者編號"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            # 從資料庫查詢最大流水號
            max_user = db.query(UserModel).filter(UserModel.id.like('USER-%')).order_by(UserModel.id.desc()).first()
            
            if max_user:
                try:
                    sequence = int(max_user.id.split('-')[-1])
                    next_sequence = sequence + 1
                except ValueError:
                    next_sequence = 1
            else:
                next_sequence = 1
            
            return f"USER-{next_sequence:03d}"
        finally:
            if should_close:
                db.close()
    
    def create_user(self, user_data: UserCreate, db: Optional[Session] = None) -> User:
        """建立使用者"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            # 檢查使用者名稱是否已存在
            existing_user = db.query(UserModel).filter(UserModel.username == user_data.username).first()
            if existing_user:
                raise ValueError("使用者名稱已存在")
            
            # 產生使用者 ID
            user_id = self._get_next_user_id(db)
            
            # 建立使用者
            user_model = UserModel(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                is_admin=user_data.is_admin,
                is_active=True,
                hashed_password=get_password_hash(user_data.password)
            )
            
            db.add(user_model)
            db.commit()
            db.refresh(user_model)
            
            # 返回使用者（不包含密碼）
            return User(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                full_name=user_model.full_name,
                phone=user_model.phone,
                address=user_model.address,
                is_admin=user_model.is_admin,
                is_active=user_model.is_active,
                created_at=user_model.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                line_user_id=user_model.line_user_id
            )
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if should_close:
                db.close()
    
    def create_line_user(self, line_user_id: str, full_name: Optional[str] = None, 
                        phone: Optional[str] = None, address: Optional[str] = None, 
                        email: Optional[str] = None, db: Optional[Session] = None) -> User:
        """
        建立 LINE 使用者（不需要密碼）
        
        參數:
            line_user_id: LINE User ID
            full_name: 使用者全名
            phone: 手機號碼
            address: 地址
            email: 電子郵件
            db: 資料庫會話（可選）
        
        返回:
            User: 建立的使用者物件
        """
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            # 使用 LINE User ID 作為使用者名稱（key）
            username = line_user_id
            
            # 檢查是否已註冊報班帳號（直接使用 LINE User ID 作為 key）
            user_model = db.query(UserModel).filter(UserModel.username == username).first()
            
            if user_model:
                # 如果已存在，更新現有使用者資料（只更新非 None 的欄位）
                if full_name is not None and full_name:
                    user_model.full_name = full_name
                if phone is not None and phone:
                    user_model.phone = phone
                if address is not None and address:
                    user_model.address = address
                if email is not None:  # email 可以是 None（可選欄位）
                    user_model.email = email
                user_model.updated_at = datetime.datetime.now()
                db.commit()
                db.refresh(user_model)
            else:
                # 產生使用者 ID
                user_id = self._get_next_user_id(db)
                
                # 建立使用者（LINE 使用者不需要密碼）
                user_model = UserModel(
                    id=user_id,
                    username=username,
                    email=email,
                    full_name=full_name or f"LINE使用者_{line_user_id[:8]}",
                    phone=phone,
                    address=address,
                    is_admin=False,
                    is_active=True,
                    hashed_password=None,  # LINE 使用者不需要密碼
                    line_user_id=line_user_id
                )
                
                db.add(user_model)
                db.commit()
                db.refresh(user_model)
            
            logger.info(f"已建立 LINE 使用者：{username} (LINE User ID: {line_user_id})")
            
            # 返回使用者（不包含密碼）
            return User(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                full_name=user_model.full_name,
                phone=user_model.phone,
                address=user_model.address,
                is_admin=user_model.is_admin,
                is_active=user_model.is_active,
                created_at=user_model.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                line_user_id=user_model.line_user_id
            )
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if should_close:
                db.close()
    
    def update_line_user(self, line_user_id: str, full_name: Optional[str] = None,
                        phone: Optional[str] = None, address: Optional[str] = None,
                        email: Optional[str] = None, db: Optional[Session] = None) -> Optional[User]:
        """
        更新 LINE 使用者資料
        
        參數:
            line_user_id: LINE User ID
            full_name: 使用者全名（不可修改）
            phone: 手機號碼
            address: 地址
            email: 電子郵件
            db: 資料庫會話（可選）
        
        返回:
            User: 更新後的使用者物件，如果使用者不存在則返回 None
        """
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            username = line_user_id
            user_model = db.query(UserModel).filter(UserModel.username == username).first()
            
            if not user_model:
                return None
            
            # 更新資料（只更新非 None 的欄位，且 full_name 不可修改）
            if phone is not None:
                user_model.phone = phone
            if address is not None:
                user_model.address = address
            if email is not None:
                user_model.email = email
            user_model.updated_at = datetime.datetime.now()
            
            db.commit()
            db.refresh(user_model)
            
            return User(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                full_name=user_model.full_name,
                phone=user_model.phone,
                address=user_model.address,
                is_admin=user_model.is_admin,
                is_active=user_model.is_active,
                created_at=user_model.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                line_user_id=user_model.line_user_id
            )
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if should_close:
                db.close()
    
    def get_user_by_username(self, username: str, db: Optional[Session] = None) -> Optional[UserInDB]:
        """根據使用者名稱取得使用者"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            user_model = db.query(UserModel).filter(UserModel.username == username).first()
            if not user_model:
                return None
            
            return UserInDB(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                full_name=user_model.full_name,
                phone=user_model.phone,
                address=user_model.address,
                is_admin=user_model.is_admin,
                is_active=user_model.is_active,
                created_at=user_model.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                line_user_id=user_model.line_user_id,
                hashed_password=user_model.hashed_password
            )
        finally:
            if should_close:
                db.close()
    
    def get_user_by_line_id(self, line_user_id: str, db: Optional[Session] = None) -> Optional[UserInDB]:
        """根據 LINE User ID 取得使用者"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            # 直接使用 LINE User ID 作為使用者名稱
            user_model = db.query(UserModel).filter(UserModel.username == line_user_id).first()
            if not user_model:
                return None
            
            return UserInDB(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                full_name=user_model.full_name,
                phone=user_model.phone,
                address=user_model.address,
                is_admin=user_model.is_admin,
                is_active=user_model.is_active,
                created_at=user_model.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                line_user_id=user_model.line_user_id,
                hashed_password=user_model.hashed_password
            )
        finally:
            if should_close:
                db.close()
    
    def is_line_user_registered(self, line_user_id: str, db: Optional[Session] = None) -> bool:
        """檢查 LINE 使用者是否已註冊報班帳號"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            # 直接使用 LINE User ID 作為使用者名稱（key）檢查
            user_model = db.query(UserModel).filter(UserModel.username == line_user_id).first()
            return user_model is not None
        finally:
            if should_close:
                db.close()
    
    def delete_line_user(self, line_user_id: str, db: Optional[Session] = None) -> bool:
        """
        取消 LINE 使用者註冊報班帳號
        
        參數:
            line_user_id: LINE User ID
            db: 資料庫會話（可選）
        
        返回:
            bool: 是否成功取消
        """
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            username = line_user_id
            
            user_model = db.query(UserModel).filter(UserModel.username == username).first()
            if not user_model:
                return False
            
            # 刪除使用者
            db.delete(user_model)
            db.commit()
            
            logger.info(f"已取消 LINE 使用者註冊報班帳號：{username} (LINE User ID: {line_user_id})")
            return True
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if should_close:
                db.close()
    
    def authenticate_user(self, username: str, password: str, db: Optional[Session] = None) -> Optional[UserInDB]:
        """驗證使用者"""
        user = self.get_user_by_username(username, db)
        if not user:
            return None
        # LINE 使用者可能沒有密碼，跳過密碼驗證
        if user.hashed_password is not None:
            if not verify_password(password, user.hashed_password):
                return None
        else:
            # LINE 使用者不需要密碼驗證，但這裡是 API 登入，需要密碼
            return None
        if not user.is_active:
            return None
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """建立 JWT Token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.datetime.utcnow() + expires_delta
        else:
            expire = datetime.datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """驗證 JWT Token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            username: Optional[str] = payload.get("sub")
            if username is None:
                return None
            return TokenData(username=username)
        except JWTError:
            return None
    
    def get_current_user_from_token(self, token: str) -> UserInDB:
        """從 Token 取得使用者（內部方法）"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無法驗證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )
        token_data = self.verify_token(token)
        if token_data is None or token_data.username is None:
            raise credentials_exception
        user = self.get_user_by_username(token_data.username)
        if user is None:
            raise credentials_exception
        return user
