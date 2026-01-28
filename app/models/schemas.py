"""
Pydantic 資料模型（用於 API）
"""
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class Job(BaseModel):
    """工作資料模型"""
    id: str
    name: str  # 臨時工作名稱
    location: str  # 工作地點
    date: str  # 工作日期，格式：YYYY-MM-DD
    shifts: List[str]  # 班別列表，例如 ["早班:08-19", "中班:14-23", "晚班:22-07"]
    location_image_url: Optional[str] = None  # 工作地點圖片 URL
    latitude: Optional[float] = None  # 緯度
    longitude: Optional[float] = None  # 經度


class Application(BaseModel):
    """報班記錄模型"""
    id: str
    job_id: str
    user_id: str
    user_name: Optional[str] = None
    shift: str  # 選擇的班別
    applied_at: str  # 報班時間


class CreateJobRequest(BaseModel):
    """建立工作請求"""
    name: str = Field(..., description="臨時工作名稱")
    location: str = Field(..., description="工作地點")
    date: str = Field(..., description="工作日期，格式：YYYY-MM-DD")
    shifts: List[str] = Field(..., description="班別列表")
    location_image_url: Optional[str] = Field(None, description="工作地點圖片 URL")
    latitude: Optional[float] = Field(None, description="緯度（可選，未提供時會自動從地址取得）")
    longitude: Optional[float] = Field(None, description="經度（可選，未提供時會自動從地址取得）")


class User(BaseModel):
    """使用者資料模型"""
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    birthday: Optional[str] = None  # 西元生日 YYYY-MM-DD
    phone: Optional[str] = None  # 手機號碼
    address: Optional[str] = None  # 地址
    id_number: Optional[str] = None  # 台灣身份證字號
    is_admin: bool = False
    is_active: bool = True
    created_at: str
    line_user_id: Optional[str] = None  # LINE User ID


class UserInDB(User):
    """資料庫中的使用者模型（包含密碼）"""
    hashed_password: Optional[str] = None  # LINE 使用者可能沒有密碼


class UserCreate(BaseModel):
    """建立使用者請求"""
    username: str = Field(..., description="使用者名稱")
    password: str = Field(..., min_length=6, description="密碼（至少6個字元）")
    email: Optional[EmailStr] = Field(None, description="電子郵件")
    full_name: Optional[str] = Field(None, description="全名")
    is_admin: bool = Field(False, description="是否為管理員")


class UserLogin(BaseModel):
    """使用者登入請求"""
    username: str = Field(..., description="使用者名稱")
    password: str = Field(..., description="密碼")


class Token(BaseModel):
    """JWT Token 回應"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 資料"""
    username: Optional[str] = None
