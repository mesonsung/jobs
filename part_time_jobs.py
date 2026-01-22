"""
Good Job 報名系統

使用 FastAPI 作為後台 API，LINE Bot 作為前台介面
包含：
1. JobService - 工作管理服務
2. ApplicationService - 報名管理服務
3. LineMessageService - LINE 訊息發送服務
4. JobHandler - 工作事件處理器
5. FastAPI 路由 - 後台管理 API
6. PartTimeJobBot - 主應用程式
"""

from fastapi import FastAPI, HTTPException, Depends, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Tuple
import requests
from flask import Flask, request
import json
import datetime
import urllib.parse
import uvicorn
import threading
import socket
import os
import hmac
import hashlib
import base64
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import timedelta

# ==================== 資料模型 ====================

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
    """報名記錄模型"""
    id: str
    job_id: str
    user_id: str
    user_name: Optional[str] = None
    shift: str  # 選擇的班別
    applied_at: str  # 報名時間

class CreateJobRequest(BaseModel):
    """建立工作請求"""
    name: str = Field(..., description="臨時工作名稱")
    location: str = Field(..., description="工作地點")
    date: str = Field(..., description="工作日期，格式：YYYY-MM-DD")
    shifts: List[str] = Field(..., description="班別列表")
    location_image_url: Optional[str] = Field(None, description="工作地點圖片 URL")
    latitude: Optional[float] = Field(None, description="緯度（可選，未提供時會自動從地址取得）")
    longitude: Optional[float] = Field(None, description="經度（可選，未提供時會自動從地址取得）")

# ==================== 認證相關資料模型 ====================

class User(BaseModel):
    """使用者資料模型"""
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None  # 手機號碼
    address: Optional[str] = None  # 地址
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

# ==================== 模組 1: 工作服務 (JobService) ====================

class JobService:
    """工作管理服務"""
    
    def __init__(self):
        # 工作儲存（實際應用中應該使用資料庫）
        # 格式：{job_id: Job}
        self.jobs: Dict[str, Job] = {}
    
    def _get_next_job_id(self) -> str:
        """
        取得下一個工作編號
        
        返回:
            str: 工作編號（格式：JOB001, JOB002, ...）
        """
        # 找出現有工作中的最大流水號
        max_sequence = 0
        for job_id in self.jobs.keys():
            if job_id.startswith('JOB') and len(job_id) > 3:
                try:
                    # 提取流水號部分（JOB001 -> 001 -> 1）
                    sequence = int(job_id[3:])
                    max_sequence = max(max_sequence, sequence)
                except ValueError:
                    continue
        
        # 下一個流水號
        next_sequence = max_sequence + 1
        # 使用 3 位數流水號，不足補零
        return f"JOB{next_sequence:03d}"
    
    def create_job(self, job_data: CreateJobRequest) -> Job:
        """
        建立工作
        
        參數:
            job_data: 工作資料
        
        返回:
            Job: 建立的工作物件
        """
        # 工作編號格式：JOB+流水號（例如：JOB001, JOB002）
        job_id = self._get_next_job_id()
        
        # 取得座標（如果未提供）
        latitude = job_data.latitude
        longitude = job_data.longitude
        
        if latitude is None or longitude is None:
            # 嘗試從地址取得座標
            coordinates = geocoding_service.get_coordinates(job_data.location)
            if coordinates:
                latitude, longitude = coordinates
            else:
                print(f"⚠️  無法取得工作地點座標：{job_data.location}")
        
        job = Job(
            id=job_id,
            name=job_data.name,
            location=job_data.location,
            date=job_data.date,
            shifts=job_data.shifts,
            location_image_url=job_data.location_image_url,
            latitude=latitude,
            longitude=longitude
        )
        
        self.jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """取得工作"""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """取得所有工作"""
        return list(self.jobs.values())
    
    def get_available_jobs(self) -> List[Job]:
        """取得可報名的工作（日期大於等於今天）"""
        today = datetime.date.today()
        available_jobs = []
        
        for job in self.jobs.values():
            try:
                job_date = datetime.datetime.strptime(job.date, '%Y-%m-%d').date()
                if job_date >= today:
                    available_jobs.append(job)
            except ValueError:
                continue
        
        # 按日期排序
        available_jobs.sort(key=lambda x: x.date)
        return available_jobs

# ==================== 模組 2: 報名服務 (ApplicationService) ====================

class ApplicationService:
    """報名管理服務"""
    
    def __init__(self):
        # 報名記錄儲存（實際應用中應該使用資料庫）
        # 格式：{application_id: Application}
        self.applications: Dict[str, Application] = {}
        # 使用者報名索引：{user_id: [application_id, ...]}
        self.user_applications: Dict[str, List[str]] = {}
        # 工作報名索引：{job_id: [application_id, ...]}
        self.job_applications: Dict[str, List[str]] = {}
    
    def create_application(self, job_id: str, user_id: str, shift: str, user_name: Optional[str] = None) -> Application:
        """
        建立報名記錄
        
        參數:
            job_id: 工作ID
            user_id: 使用者ID
            shift: 選擇的班別
            user_name: 使用者名稱（可選）
        
        返回:
            Application: 報名記錄
        """
        # 報名編號格式：工作編號-日期-流水號
        # 例如：JOB001-20260110-001
        
        # 取得當前日期（YYYYMMDD格式）
        today = datetime.datetime.now().strftime('%Y%m%d')
        
        # 計算該工作在同一天的流水號
        # 找出該工作在同一天的所有報名記錄
        same_day_applications = []
        for app_id, app in self.applications.items():
            if app.job_id == job_id:
                # 檢查報名時間是否為同一天
                app_date = app.applied_at.split()[0].replace('-', '')  # 提取日期部分並移除連字號
                if app_date == today:
                    same_day_applications.append(app_id)
        
        # 流水號 = 當天報名數量 + 1（3位數，補零）
        sequence_number = len(same_day_applications) + 1
        sequence_str = f"{sequence_number:03d}"
        
        # 組合報名編號：工作編號-日期-流水號
        application_id = f"{job_id}-{today}-{sequence_str}"
        
        application = Application(
            id=application_id,
            job_id=job_id,
            user_id=user_id,
            user_name=user_name,
            shift=shift,
            applied_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        self.applications[application_id] = application
        
        # 更新索引
        if user_id not in self.user_applications:
            self.user_applications[user_id] = []
        self.user_applications[user_id].append(application_id)
        
        if job_id not in self.job_applications:
            self.job_applications[job_id] = []
        self.job_applications[job_id].append(application_id)
        
        return application
    
    def get_user_application_for_job(self, user_id: str, job_id: str) -> Optional[Application]:
        """取得使用者對特定工作的報名記錄"""
        user_app_ids = self.user_applications.get(user_id, [])
        for app_id in user_app_ids:
            app = self.applications.get(app_id)
            if app and app.job_id == job_id:
                return app
        return None
    
    def cancel_application(self, user_id: str, job_id: str) -> Tuple[bool, Optional[Application]]:
        """
        取消報名
        
        參數:
            user_id: 使用者ID
            job_id: 工作ID
        
        返回:
            tuple: (是否成功, 取消的報名記錄)
        """
        application = self.get_user_application_for_job(user_id, job_id)
        if not application:
            return False, None
        
        # 移除報名記錄
        app_id = application.id
        if app_id in self.applications:
            del self.applications[app_id]
        
        # 更新索引
        if user_id in self.user_applications:
            if app_id in self.user_applications[user_id]:
                self.user_applications[user_id].remove(app_id)
        
        if job_id in self.job_applications:
            if app_id in self.job_applications[job_id]:
                self.job_applications[job_id].remove(app_id)
        
        return True, application
    
    def get_job_applications(self, job_id: str) -> List[Application]:
        """取得工作的所有報名記錄"""
        app_ids = self.job_applications.get(job_id, [])
        applications = []
        for app_id in app_ids:
            app = self.applications.get(app_id)
            if app:
                applications.append(app)
        return applications
    
    def get_user_applications(self, user_id: str) -> List[Application]:
        """
        取得使用者的所有報名記錄
        
        參數:
            user_id: 使用者ID
        
        返回:
            list: 報名記錄列表
        """
        app_ids = self.user_applications.get(user_id, [])
        applications = []
        for app_id in app_ids:
            app = self.applications.get(app_id)
            if app:
                applications.append(app)
        # 按報名時間排序（最新的在前）
        applications.sort(key=lambda x: x.applied_at, reverse=True)
        return applications

# ==================== 模組 2.5: Google Geocoding 服務 ====================

# Google Maps API Key 設定（可在主程式區塊覆蓋）
_DEFAULT_GOOGLE_MAPS_API_KEY = "AIzaSyDqcXhRP7pJmQIlO_F86Oh8lSmEtOUgXaw"

class GeocodingService:
    """Google Maps Geocoding 服務"""
    
    def __init__(self, default_api_key: str = ""):
        # 優先使用環境變數，其次使用傳入的預設值，最後使用模組預設值
        env_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if env_key:
            self.api_key = env_key
        elif default_api_key:
            self.api_key = default_api_key
        else:
            self.api_key = _DEFAULT_GOOGLE_MAPS_API_KEY
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def get_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """
        根據地址取得經緯度座標
        
        參數:
            address: 地址字串
        
        返回:
            Optional[Tuple[float, float]]: (緯度, 經度) 或 None（如果失敗）
        """
        if not self.api_key:
            print("⚠️  警告：未設定 GOOGLE_MAPS_API_KEY，無法取得座標")
            return None
        
        try:
            params = {
                "address": address,
                "key": self.api_key,
                "language": "zh-TW"  # 使用繁體中文
            }
            
            response = requests.get(self.geocoding_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                latitude = location.get("lat")
                longitude = location.get("lng")
                
                if latitude and longitude:
                    print(f"✅ 成功取得座標：{address} -> ({latitude}, {longitude})")
                    return (float(latitude), float(longitude))
                else:
                    print(f"⚠️  警告：無法從回應中取得座標：{address}")
                    return None
            else:
                status = data.get("status", "UNKNOWN")
                print(f"⚠️  Geocoding API 錯誤：{status} - {address}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Geocoding API 請求錯誤：{e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            print(f"❌ 解析 Geocoding 回應錯誤：{e}")
            return None
        except Exception as e:
            print(f"❌ 取得座標時發生未預期錯誤：{e}")
            return None
    
    def get_address_from_coordinates(self, latitude: float, longitude: float) -> Optional[str]:
        """
        根據經緯度取得地址（反向地理編碼）
        
        參數:
            latitude: 緯度
            longitude: 經度
        
        返回:
            Optional[str]: 地址字串或 None（如果失敗）
        """
        if not self.api_key:
            print("⚠️  警告：未設定 GOOGLE_MAPS_API_KEY，無法取得地址")
            return None
        
        try:
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self.api_key,
                "language": "zh-TW"  # 使用繁體中文
            }
            
            response = requests.get(self.geocoding_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                formatted_address = data["results"][0].get("formatted_address")
                if formatted_address:
                    print(f"✅ 成功取得地址：({latitude}, {longitude}) -> {formatted_address}")
                    return formatted_address
                else:
                    print(f"⚠️  警告：無法從回應中取得地址：({latitude}, {longitude})")
                    return None
            else:
                status = data.get("status", "UNKNOWN")
                print(f"⚠️  Reverse Geocoding API 錯誤：{status} - ({latitude}, {longitude})")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Reverse Geocoding API 請求錯誤：{e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"❌ 解析 Reverse Geocoding 回應錯誤：{e}")
            return None
        except Exception as e:
            print(f"❌ 取得地址時發生未預期錯誤：{e}")
            return None

# 全域 Geocoding 服務實例（稍後在主程式區塊會重新初始化）
geocoding_service = GeocodingService()

# ==================== 模組 2.5: 認證服務 (AuthService) ====================

# JWT 設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 天

# 密碼加密設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 設定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class AuthService:
    """認證服務"""
    
    def __init__(self):
        # 使用者儲存（實際應用中應該使用資料庫）
        # 格式：{username: UserInDB}
        self.users: Dict[str, UserInDB] = {}
        # 使用者 ID 索引：{user_id: username}
        self.user_ids: Dict[str, str] = {}
        # LINE User ID 索引：{line_user_id: username}
        self.line_user_ids: Dict[str, str] = {}
        self._create_default_admin()
    
    def _create_default_admin(self):
        """建立預設管理員帳號"""
        default_admin_username = os.getenv("ADMIN_USERNAME", "admin")
        default_admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        if default_admin_username not in self.users:
            admin_user = UserInDB(
                id="USER-ADMIN-001",
                username=default_admin_username,
                email="admin@example.com",
                full_name="系統管理員",
                is_admin=True,
                is_active=True,
                created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                hashed_password=self._get_password_hash(default_admin_password)
            )
            self.users[default_admin_username] = admin_user
            self.user_ids["USER-ADMIN-001"] = default_admin_username
            print(f"✅ 已建立預設管理員帳號：{default_admin_username}")
    
    def _get_password_hash(self, password: str) -> str:
        """加密密碼"""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """驗證密碼"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _get_next_user_id(self) -> str:
        """取得下一個使用者編號"""
        max_sequence = 0
        for user_id in self.user_ids.keys():
            if user_id.startswith('USER-') and len(user_id) > 9:
                try:
                    sequence = int(user_id.split('-')[-1])
                    max_sequence = max(max_sequence, sequence)
                except ValueError:
                    continue
        
        next_sequence = max_sequence + 1
        return f"USER-{next_sequence:03d}"
    
    def create_user(self, user_data: UserCreate) -> User:
        """建立使用者"""
        # 檢查使用者名稱是否已存在
        if user_data.username in self.users:
            raise ValueError("使用者名稱已存在")
        
        # 產生使用者 ID
        user_id = self._get_next_user_id()
        
        # 建立使用者
        user_in_db = UserInDB(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            is_admin=user_data.is_admin,
            is_active=True,
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            hashed_password=self._get_password_hash(user_data.password)
        )
        
        self.users[user_data.username] = user_in_db
        self.user_ids[user_id] = user_data.username
        
        # 返回使用者（不包含密碼）
        return User(
            id=user_in_db.id,
            username=user_in_db.username,
            email=user_in_db.email,
            full_name=user_in_db.full_name,
            is_admin=user_in_db.is_admin,
            is_active=user_in_db.is_active,
            created_at=user_in_db.created_at,
            line_user_id=user_in_db.line_user_id
        )
    
    def create_line_user(self, line_user_id: str, full_name: Optional[str] = None, 
                        phone: Optional[str] = None, address: Optional[str] = None, 
                        email: Optional[str] = None) -> User:
        """
        建立 LINE 使用者（不需要密碼）
        
        參數:
            line_user_id: LINE User ID
            full_name: 使用者全名
            phone: 手機號碼
            address: 地址
            email: 電子郵件
        
        返回:
            User: 建立的使用者物件
        """
        # 使用 LINE User ID 作為使用者名稱（key）
        username = line_user_id
        
        # 檢查是否已註冊（直接使用 LINE User ID 作為 key）
        if username in self.users:
            # 如果已存在，更新現有使用者資料（只更新非 None 的欄位）
            user_in_db = self.users[username]
            # 更新資料（如果提供新值則更新）
            if full_name is not None and full_name:
                user_in_db.full_name = full_name
            if phone is not None and phone:
                user_in_db.phone = phone
            if address is not None and address:
                user_in_db.address = address
            if email is not None:  # email 可以是 None（可選欄位）
                user_in_db.email = email
        else:
            # 產生使用者 ID
            user_id = self._get_next_user_id()
            
            # 建立使用者（LINE 使用者不需要密碼）
            user_in_db = UserInDB(
                id=user_id,
                username=username,
                email=email,
                full_name=full_name or f"LINE使用者_{line_user_id[:8]}",
                phone=phone,
                address=address,
                is_admin=False,
                is_active=True,
                created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                hashed_password=None,  # LINE 使用者不需要密碼
                line_user_id=line_user_id
            )
            
            self.users[username] = user_in_db
            self.user_ids[user_id] = username
            # 保留 line_user_ids 索引以向後兼容（但現在 username = line_user_id）
            self.line_user_ids[line_user_id] = username
        
        print(f"✅ 已建立 LINE 使用者：{username} (LINE User ID: {line_user_id})")
        
        # 返回使用者（不包含密碼）
        return User(
            id=user_in_db.id,
            username=user_in_db.username,
            email=user_in_db.email,
            full_name=user_in_db.full_name,
            phone=user_in_db.phone,
            address=user_in_db.address,
            is_admin=user_in_db.is_admin,
            is_active=user_in_db.is_active,
            created_at=user_in_db.created_at,
            line_user_id=user_in_db.line_user_id
        )
    
    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """根據使用者名稱取得使用者"""
        return self.users.get(username)
    
    def get_user_by_line_id(self, line_user_id: str) -> Optional[UserInDB]:
        """根據 LINE User ID 取得使用者"""
        # 直接使用 LINE User ID 作為使用者名稱
        return self.users.get(line_user_id)
    
    def is_line_user_registered(self, line_user_id: str) -> bool:
        """檢查 LINE 使用者是否已註冊"""
        # 直接使用 LINE User ID 作為使用者名稱（key）檢查
        return line_user_id in self.users
    
    def delete_line_user(self, line_user_id: str) -> bool:
        """
        取消 LINE 使用者註冊
        
        參數:
            line_user_id: LINE User ID
        
        返回:
            bool: 是否成功取消
        """
        username = line_user_id
        
        if username not in self.users:
            return False
        
        user = self.users.get(username)
        if not user:
            return False
        
        # 取消使用者註冊
        user_id = user.id
        del self.users[username]
        
        # 刪除索引
        if user_id in self.user_ids:
            del self.user_ids[user_id]
        
        if line_user_id in self.line_user_ids:
            del self.line_user_ids[line_user_id]
        
        print(f"✅ 已取消 LINE 使用者註冊：{username} (LINE User ID: {line_user_id})")
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        """驗證使用者"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        # LINE 使用者可能沒有密碼，跳過密碼驗證
        if user.hashed_password is not None:
            if not self._verify_password(password, user.hashed_password):
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
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """驗證 JWT Token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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

# 全域認證服務實例
auth_service = AuthService()

# 依賴注入函數
def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """取得當前使用者（從 Token）"""
    return auth_service.get_current_user_from_token(token)

def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """取得當前活躍使用者"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="使用者帳號已停用")
    return current_user

def require_admin(current_user: UserInDB = Depends(get_current_active_user)) -> UserInDB:
    """要求管理員權限"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return current_user

# ==================== 模組 3: LINE 訊息服務 (LineMessageService) ====================

class LineMessageService:
    """LINE 訊息發送服務"""
    
    def __init__(self, channel_access_token: str):
        self.token = channel_access_token
        self.api_url = "https://api.line.me/v2/bot/message/reply"
    
    def _get_headers(self) -> Dict[str, str]:
        """取得 API 請求標頭"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def send_text(self, reply_token: str, text: str) -> requests.Response:
        """發送文字訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": [{
                "type": "text",
                "text": text
            }]
        }
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )
    
    def send_flex_message(self, reply_token: str, alt_text: str, contents: Dict) -> requests.Response:
        """發送 Flex 訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": [{
                "type": "flex",
                "altText": alt_text,
                "contents": contents
            }]
        }
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )
    
    def send_multiple_messages(self, reply_token: str, messages: List[Dict]) -> requests.Response:
        """在同一個回覆中發送多個訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": messages
        }
        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()  # 如果狀態碼不是 2xx，會拋出異常
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ LINE API 錯誤：{e}")
            if hasattr(e.response, 'text'):
                print(f"   回應內容：{e.response.text}")
            raise
    
    def send_buttons_template(self, reply_token: str, title: str, text: str, actions: List[Dict]) -> requests.Response:
        """發送按鈕範本訊息"""
        buttons_template = {
            "type": "template",
            "altText": title,
            "template": {
                "type": "buttons",
                "title": title,
                "text": text,
                "actions": actions
            }
        }
        
        payload = {
            "replyToken": reply_token,
            "messages": [buttons_template]
        }
        
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )

# ==================== 模組 4: 工作處理器 (JobHandler) ====================

class JobHandler:
    """工作事件處理器"""
    
    def __init__(self, job_service: JobService, application_service: ApplicationService, message_service: LineMessageService, auth_service: Optional[AuthService] = None):
        self.job_service = job_service
        self.application_service = application_service
        self.message_service = message_service
        self.auth_service = auth_service
        # 註冊狀態管理：{user_id: {'step': step, 'data': {...}}}
        self.registration_states: Dict[str, Dict] = {}
        # 修改資料狀態管理：{user_id: {'step': step, 'field': field_name}}
        self.edit_profile_states: Dict[str, Dict] = {}
    
    def show_available_jobs(self, reply_token: str, user_id: Optional[str] = None) -> None:
        """顯示可報名的工作列表"""
        jobs = self.job_service.get_available_jobs()
        
        print(f"📋 查詢可報名工作：找到 {len(jobs)} 個工作")
        
        if not jobs:
            self.message_service.send_text(
                reply_token,
                "目前沒有可報名的工作。\n\n請稍後再試，或聯絡管理員。\n\n💡 提示：管理員可以透過 API 發佈新工作。"
            )
            return
        
        # 建立工作列表訊息
        messages = []
        messages.append({
            "type": "text",
            "text": f"📋 可報名的工作（共 {len(jobs)} 個）："
        })
        
        # 每個工作建立一個 Flex 訊息或按鈕訊息
        for job in jobs:
            # 檢查使用者是否已報名
            is_applied = False
            applied_shift = None
            if user_id:
                application = self.application_service.get_user_application_for_job(user_id, job.id)
                if application:
                    is_applied = True
                    applied_shift = application.shift
            
            # 建立狀態標示
            status_icon = "✅ 已報名" if is_applied else "⭕ 未報名"
            status_text = f"\n{status_icon}"
            if is_applied and applied_shift:
                status_text += f" ({applied_shift})"
            
            # 建立 Google Maps 導航 URL
            encoded_location = urllib.parse.quote(job.location)
            navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
            
            # 檢查使用者是否已註冊
            is_registered = True
            if self.auth_service:
                is_registered = self.auth_service.is_line_user_registered(user_id) if user_id else False
            
            # 建立按鈕動作
            actions = [
                {
                    "type": "postback",
                    "label": "查看詳情",
                    "data": f"action=job&step=detail&job_id={job.id}"
                }
            ]
            
            # 如果未註冊，加入註冊按鈕
            if not is_registered:
                actions.append({
                    "type": "postback",
                    "label": "📝 註冊",
                    "data": "action=register&step=register"
                })
            # 根據報名狀態加入不同按鈕
            elif is_applied:
                # 已報名：加入取消報名按鈕
                actions.append({
                    "type": "postback",
                    "label": "取消報名",
                    "data": f"action=job&step=cancel&job_id={job.id}"
                })
            else:
                # 未報名：加入報名按鈕
                actions.append({
                    "type": "postback",
                    "label": "報名",
                    "data": f"action=job&step=apply&job_id={job.id}"
                })
            
            # 加入導航按鈕
            actions.append({
                "type": "uri",
                "label": "導航",
                "uri": navigation_url
            })
            
            # 建立按鈕範本文字（確保不超過 60 字元，包括換行符）
            # 簡化地點顯示（如果太長）
            location_display = job.location
            max_location_len = 18
            if len(location_display) > max_location_len:
                location_display = location_display[:max_location_len-3] + "..."
            
            # 建立班別顯示文字
            if len(job.shifts) == 1:
                shifts_display = job.shifts[0]
            elif len(job.shifts) == 2:
                shifts_display = ", ".join(job.shifts)
            else:
                # 多個班別時，只顯示第一個和總數
                shifts_display = f"{job.shifts[0]}等{len(job.shifts)}個"
            
            # 建立基本文字（不含狀態）
            base_text = f"📍{location_display}\n📅{job.date}\n⏰{shifts_display}"
            
            # 嘗試加入狀態文字
            if is_applied:
                status_display = "\n✅已報名"
                if applied_shift and len(applied_shift) <= 10:
                    status_display += f"({applied_shift[:8]})"
            else:
                status_display = "\n⭕未報名"
            
            # 檢查總長度（換行符算 1 個字元）
            test_text = base_text + status_display
            if len(test_text) <= 60:
                job_text = test_text
            else:
                # 如果太長，簡化班別顯示
                if len(job.shifts) > 1:
                    shifts_display = f"{len(job.shifts)}個班別"
                else:
                    shifts_display = job.shifts[0][:10] if job.shifts else ""
                
                base_text = f"📍{location_display}\n📅{job.date}\n⏰{shifts_display}"
                test_text = base_text + status_display
                
                if len(test_text) <= 60:
                    job_text = test_text
                else:
                    # 最後手段：只顯示基本資訊，不顯示狀態
                    job_text = base_text
            
            template = {
                "type": "buttons",
                "title": job.name[:40],  # LINE 限制標題長度
                "text": job_text,
                "actions": actions
            }
            
            # 如果有圖片，加入縮圖（LINE API 不接受 None 值）
            if job.location_image_url:
                template["thumbnailImageUrl"] = job.location_image_url
                # 也可以選擇發送單獨的圖片訊息
                # messages.append({
                #     "type": "image",
                #     "originalContentUrl": job.location_image_url,
                #     "previewImageUrl": job.location_image_url
                # })
            
            messages.append({
                "type": "template",
                "altText": job.name,
                "template": template
            })
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def show_job_detail(self, reply_token: str, user_id: str, job_id: str) -> None:
        """顯示工作詳情"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查使用者是否已註冊
        is_registered = True
        if self.auth_service:
            is_registered = self.auth_service.is_line_user_registered(user_id)
        
        # 檢查使用者是否已報名
        application = None
        is_applied = False
        if is_registered:
            application = self.application_service.get_user_application_for_job(user_id, job_id)
            is_applied = application is not None
        
        # 建立工作詳情訊息
        job_detail = f"""📌 {job.name}

📍 工作地點：{job.location}
📅 工作日期：{job.date}
⏰ 可選班別：
"""
        for shift in job.shifts:
            job_detail += f"   • {shift}\n"
        
        if is_applied and application:
            job_detail += f"\n✅ 您已報名：{application.shift}"
        
        # 建立 Google Maps 導航 URL
        encoded_location = urllib.parse.quote(job.location)
        navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
        
        # 建立按鈕
        actions = []
        if not is_registered:
            # 未註冊使用者：顯示註冊按鈕
            actions.append({
                "type": "postback",
                "label": "📝 註冊",
                "data": "action=register&step=register"
            })
        elif is_applied:
            actions.append({
                "type": "postback",
                "label": "取消報名",
                "data": f"action=job&step=cancel&job_id={job_id}"
            })
        else:
            actions.append({
                "type": "postback",
                "label": "報名",
                "data": f"action=job&step=apply&job_id={job_id}"
            })
        
        # 加入導航按鈕
        actions.append({
            "type": "uri",
            "label": "導航",
            "uri": navigation_url
        })
        
        actions.append({
            "type": "postback",
            "label": "返回工作列表",
            "data": "action=job&step=list"
        })
        
        messages = []
        
        # 如果有圖片，先發送圖片
        if job.location_image_url:
            messages.append({
                "type": "image",
                "originalContentUrl": job.location_image_url,
                "previewImageUrl": job.location_image_url
            })
        
        messages.append({
            "type": "text",
            "text": job_detail
        })
        
        messages.append({
            "type": "template",
            "altText": job.name,
            "template": {
                "type": "buttons",
                "title": job.name,
                "text": "請選擇操作：",
                "actions": actions
            }
        })
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_apply_job(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理報名工作流程 - 顯示班別選擇"""
        # 檢查使用者是否已註冊
        if self.auth_service and not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法報名工作。\n\n請先使用「註冊」功能完成註冊。"
            )
            return
        
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查是否已報名
        existing_app = self.application_service.get_user_application_for_job(user_id, job_id)
        if existing_app:
            self.message_service.send_text(
                reply_token,
                f"❌ 您已經報名了這個工作（班別：{existing_app.shift}）\n\n如需取消，請先取消現有報名。"
            )
            return
        
        # 建立班別選擇按鈕（最多4個）
        shift_actions = []
        for shift in job.shifts[:4]:  # LINE 按鈕最多4個
            shift_actions.append({
                "type": "postback",
                "label": shift,
                "data": f"action=job&step=select_shift&job_id={job_id}&shift={urllib.parse.quote(shift)}"
            })
        
        messages = [
            {
                "type": "text",
                "text": f"請選擇要報名的班別：\n\n工作：{job.name}\n日期：{job.date}"
            },
            {
                "type": "template",
                "altText": "選擇班別",
                "template": {
                    "type": "buttons",
                    "title": "選擇班別",
                    "text": "請選擇您要報名的班別：",
                    "actions": shift_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_select_shift(self, reply_token: str, user_id: str, job_id: str, shift: str) -> None:
        """處理選擇班別並完成報名"""
        # 檢查使用者是否已註冊
        if self.auth_service and not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法報名工作。\n\n請先使用「註冊」功能完成註冊。"
            )
            return
        
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        # 檢查班別是否有效
        if shift not in job.shifts:
            self.message_service.send_text(reply_token, "❌ 無效的班別選擇。")
            return
        
        # 檢查是否已報名
        existing_app = self.application_service.get_user_application_for_job(user_id, job_id)
        if existing_app:
            self.message_service.send_text(
                reply_token,
                f"❌ 您已經報名了這個工作（班別：{existing_app.shift}）"
            )
            return
        
        # 建立報名記錄
        application = self.application_service.create_application(job_id, user_id, shift)
        
        # 發送報名成功訊息
        success_message = f"""✅ 報名成功！

📋 報名資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 報名班別：{shift}
• 報名時間：{application.applied_at}
• 報名編號：{application.id}

感謝您的報名，我們會盡快與您聯繫！"""
        
        self.message_service.send_text(reply_token, success_message)
    
    def handle_cancel_application(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理取消報名流程 - 顯示報名資訊和確認按鈕"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        application = self.application_service.get_user_application_for_job(user_id, job_id)
        if not application:
            self.message_service.send_text(reply_token, "❌ 您尚未報名這個工作。")
            return
        
        # 顯示報名資訊和確認按鈕
        cancel_text = f"""請確認要取消的報名：

📋 報名資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 報名班別：{application.shift}
• 報名時間：{application.applied_at}
• 報名編號：{application.id}"""
        
        actions = [
            {
                "type": "postback",
                "label": "確認取消",
                "data": f"action=job&step=confirm_cancel&job_id={job_id}"
            },
            {
                "type": "postback",
                "label": "不取消",
                "data": f"action=job&step=detail&job_id={job_id}"
            }
        ]
        
        messages = [
            {
                "type": "text",
                "text": cancel_text
            },
            {
                "type": "template",
                "altText": "確認取消報名",
                "template": {
                    "type": "buttons",
                    "title": "確認取消報名",
                    "text": "確定要取消這個報名嗎？",
                    "actions": actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_confirm_cancel(self, reply_token: str, user_id: str, job_id: str) -> None:
        """處理確認取消報名"""
        job = self.job_service.get_job(job_id)
        if not job:
            self.message_service.send_text(reply_token, "❌ 找不到指定的工作。")
            return
        
        success, canceled_app = self.application_service.cancel_application(user_id, job_id)
        
        if success and canceled_app:
            cancel_message = f"""✅ 報名已成功取消！

📋 已取消的報名資訊：
• 工作名稱：{job.name}
• 工作地點：{job.location}
• 工作日期：{job.date}
• 原報名班別：{canceled_app.shift}
• 報名編號：{canceled_app.id}

如有任何問題，歡迎隨時聯絡我們。"""
            self.message_service.send_text(reply_token, cancel_message)
        else:
            self.message_service.send_text(reply_token, "❌ 取消報名失敗，請稍後再試。")
    
    def show_user_applications(self, reply_token: str, user_id: str) -> None:
        """顯示使用者已報名的工作列表"""
        applications = self.application_service.get_user_applications(user_id)
        
        if not applications:
            self.message_service.send_text(
                reply_token,
                "📋 您目前沒有任何報名記錄。\n\n請使用「查看工作列表」來尋找並報名工作。"
            )
            return
        
        # 建立報名列表訊息
        messages = []
        messages.append({
            "type": "text",
            "text": f"📋 您的報名記錄（共 {len(applications)} 筆）："
        })
        
        # 每個報名建立一個訊息卡片
        for i, app in enumerate(applications, 1):
            job = self.job_service.get_job(app.job_id)
            
            if not job:
                # 如果工作不存在，只顯示報名資訊
                app_text = f"{i}. 報名編號：{app.id}\n   班別：{app.shift}\n   報名時間：{app.applied_at}\n   ⚠️ 工作已不存在"
                messages.append({
                    "type": "text",
                    "text": app_text
                })
                continue
            
            # 建立報名資訊文字（確保不超過 60 字元）
            # 簡化工作名稱和地點
            job_name_display = job.name[:15] if len(job.name) > 15 else job.name
            location_display = job.location[:12] if len(job.location) > 12 else job.location
            if len(job.location) > 12:
                location_display += "..."
            
            # 簡化報名編號（顯示日期+流水號，例如：20260110-001）
            # 報名編號格式：工作編號-日期-流水號
            # 提取最後部分（日期-流水號）
            if '-' in app.id:
                parts = app.id.split('-')
                if len(parts) >= 2:
                    # 取最後兩部分：日期和流水號
                    app_id_display = f"{parts[-2]}-{parts[-1]}"
                else:
                    app_id_display = app.id[-12:] if len(app.id) > 12 else app.id
            else:
                app_id_display = app.id[-12:] if len(app.id) > 12 else app.id
            
            # 簡化報名時間（只顯示日期）
            applied_date = app.applied_at.split()[0] if " " in app.applied_at else app.applied_at
            
            # 建立文字，逐步檢查長度
            app_text = f"📌{job_name_display}\n📍{location_display}\n📅{job.date}\n⏰{app.shift}"
            
            # 如果還有空間，加入報名編號
            test_text = app_text + f"\n🆔{app_id_display}"
            if len(test_text) <= 60:
                app_text = test_text
                # 如果還有更多空間，加入報名時間
                test_text = app_text + f"\n📝{applied_date}"
                if len(test_text) <= 60:
                    app_text = test_text
            
            # 建立 Google Maps 導航 URL
            encoded_location = urllib.parse.quote(job.location)
            navigation_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_location}"
            
            # 檢查使用者是否已註冊
            is_registered = True
            if self.auth_service:
                is_registered = self.auth_service.is_line_user_registered(user_id)
            
            # 建立按鈕動作
            actions = [
                {
                    "type": "postback",
                    "label": "查看詳情",
                    "data": f"action=job&step=detail&job_id={job.id}"
                }
            ]
            
            if is_registered:
                actions.extend([
                    {
                        "type": "postback",
                        "label": "取消報名",
                        "data": f"action=job&step=cancel&job_id={job.id}"
                    },
                    {
                        "type": "uri",
                        "label": "導航",
                        "uri": navigation_url
                    }
                ])
            else:
                actions.append({
                    "type": "postback",
                    "label": "📝 註冊",
                    "data": "action=register&step=register"
                })
            
            # 建立按鈕範本
            template = {
                "type": "buttons",
                "title": f"報名#{i}",
                "text": app_text,
                "actions": actions
            }
            
            # 如果有圖片，加入縮圖
            if job.location_image_url:
                template["thumbnailImageUrl"] = job.location_image_url
            
            messages.append({
                "type": "template",
                "altText": f"報名記錄 #{i} - {job.name}",
                "template": template
            })
        
        # 如果報名記錄很多，加入返回按鈕
        if len(applications) > 1:
            messages.append({
                "type": "template",
                "altText": "操作選單",
                "template": {
                    "type": "buttons",
                    "text": "請選擇操作：",
                    "actions": [
                        {
                            "type": "postback",
                            "label": "返回主選單",
                            "data": "action=job&step=menu"
                        },
                        {
                            "type": "postback",
                            "label": "查看工作列表",
                            "data": "action=job&step=list"
                        }
                    ]
                }
            })
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_register(self, reply_token: str, user_id: str) -> None:
        """處理 LINE 使用者註冊 - 開始註冊流程"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 註冊功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if self.auth_service.is_line_user_registered(user_id):
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                user_info = f"""✅ 您已經註冊過了！

📋 您的帳號資訊：
• 姓名：{user.full_name or '未填寫'}
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}"""
                self.message_service.send_text(reply_token, user_info)
            return
        
        # 開始註冊流程 - 第一步：輸入姓名
        self.registration_states[user_id] = {
            'step': 'name',
            'data': {}
        }
        
        self.message_service.send_text(
            reply_token,
            "📝 歡迎註冊！請依序填寫以下資料：\n\n第一步：請輸入您的姓名"
        )
    
    def handle_register_input(self, reply_token: str, user_id: str, text: str) -> None:
        """處理註冊資料輸入"""
        if not self.auth_service:
            return
        
        # 檢查是否在註冊流程中
        if user_id not in self.registration_states:
            return
        
        # 檢查是否要取消註冊
        if text.strip().lower() in ['取消', 'cancel', '取消註冊']:
            del self.registration_states[user_id]
            self.message_service.send_text(
                reply_token,
                "❌ 已取消註冊流程。\n\n如需註冊，請重新發送「註冊」。"
            )
            return
        
        state = self.registration_states[user_id]
        step = state['step']
        data = state['data']
        
        if step == 'name':
            # 儲存姓名，進入下一步
            name = text.strip()
            if not name:
                self.message_service.send_text(
                    reply_token,
                    "❌ 姓名不能為空，請重新輸入。"
                )
                return
            data['full_name'] = name
            state['step'] = 'phone'
            self.message_service.send_text(
                reply_token,
                f"✅ 姓名已記錄：{data['full_name']}\n\n第二步：請輸入您的手機號碼\n（格式：09XX-XXX-XXX 或 09XXXXXXXX）"
            )
        
        elif step == 'phone':
            # 驗證並儲存手機號碼
            phone = text.strip().replace('-', '').replace(' ', '')
            # 簡單驗證：台灣手機號碼格式
            if not phone.isdigit() or len(phone) != 10 or not phone.startswith('09'):
                self.message_service.send_text(
                    reply_token,
                    "❌ 手機號碼格式不正確，請輸入10位數手機號碼（例如：0912345678）"
                )
                return
            
            data['phone'] = phone
            state['step'] = 'address'
            self.message_service.send_text(
                reply_token,
                f"✅ 手機號碼已記錄：{data['phone']}\n\n第三步：請輸入您的地址"
            )
        
        elif step == 'address':
            # 儲存地址，進入下一步
            address = text.strip()
            if not address:
                self.message_service.send_text(
                    reply_token,
                    "❌ 地址不能為空，請重新輸入。"
                )
                return
            data['address'] = address
            state['step'] = 'email'
            self.message_service.send_text(
                reply_token,
                f"✅ 地址已記錄：{data['address']}\n\n第四步：請輸入您的 Email\n（可選，直接輸入「跳過」即可）"
            )
        
        elif step == 'email':
            # 處理 Email（可選）
            email = text.strip()
            if email.lower() in ['跳過', 'skip', '略過', '']:
                data['email'] = None
            else:
                # 簡單的 Email 驗證
                if '@' not in email or '.' not in email.split('@')[-1]:
                    self.message_service.send_text(
                        reply_token,
                        "❌ Email 格式不正確，請重新輸入或輸入「跳過」"
                    )
                    return
                data['email'] = email
            
            # 完成註冊
            try:
                # 取得並驗證必填欄位
                full_name = data.get('full_name', '').strip()
                phone = data.get('phone', '').strip()
                address = data.get('address', '').strip()
                email = data.get('email')  # email 可能是 None（可選）
                if email:
                    email = email.strip() if email else None
                
                # 驗證必填欄位
                if not full_name:
                    self.message_service.send_text(
                        reply_token,
                        "❌ 姓名為必填欄位，請重新開始註冊流程。"
                    )
                    if user_id in self.registration_states:
                        del self.registration_states[user_id]
                    return
                
                if not phone:
                    self.message_service.send_text(
                        reply_token,
                        "❌ 手機號碼為必填欄位，請重新開始註冊流程。"
                    )
                    if user_id in self.registration_states:
                        del self.registration_states[user_id]
                    return
                
                if not address:
                    self.message_service.send_text(
                        reply_token,
                        "❌ 地址為必填欄位，請重新開始註冊流程。"
                    )
                    if user_id in self.registration_states:
                        del self.registration_states[user_id]
                    return
                
                # 建立使用者（確保所有欄位都有值）
                user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=full_name,
                    phone=phone,
                    address=address,
                    email=email
                )
                
                # 清除註冊狀態
                del self.registration_states[user_id]
                
                success_message = f"""✅ 註冊成功！

📋 您的註冊資訊：
• 姓名：{user.full_name}
• 手機：{user.phone}
• 地址：{user.address}
• Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}

現在您可以開始報名工作了！"""
                
                # 使用 send_multiple_messages 在同一個回覆中發送成功訊息和主選單
                # 先準備主選單的內容（與 show_main_menu 一致）
                is_registered = True  # 剛註冊完成，一定是已註冊狀態
                actions = []
                
                actions.extend([
                    {
                        "type": "postback",
                        "label": "查看工作列表",
                        "data": "action=job&step=list"
                    },
                    {
                        "type": "postback",
                        "label": "查詢已報名",
                        "data": "action=job&step=my_applications"
                    }
                ])
                
                # 已註冊使用者：顯示查看註冊資料選項
                if is_registered:
                    actions.append({
                        "type": "postback",
                        "label": "👤 查看註冊資料",
                        "data": "action=view_profile&step=view"
                    })
                
                actions.append({
                    "type": "message",
                    "label": "聯絡客服",
                    "text": "我需要客服協助"
                })
                
                menu_text = "請選擇您需要的服務："
                
                messages = [
                    {
                        "type": "text",
                        "text": success_message
                    },
                    {
                        "type": "template",
                        "altText": "主選單",
                        "template": {
                            "type": "buttons",
                            "title": "Good Job 報名系統",
                            "text": menu_text,
                            "actions": actions
                        }
                    }
                ]
                
                self.message_service.send_multiple_messages(reply_token, messages)
            except Exception as e:
                print(f"❌ 註冊失敗：{e}")
                import traceback
                traceback.print_exc()
                # 清除註冊狀態
                if user_id in self.registration_states:
                    del self.registration_states[user_id]
                self.message_service.send_text(
                    reply_token,
                    f"❌ 註冊失敗：{str(e)}\n\n請稍後再試或聯絡客服。"
                )
    
    def handle_edit_profile(self, reply_token: str, user_id: str) -> None:
        """處理修改註冊資料 - 選擇要修改的欄位"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 修改註冊資料功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法修改註冊資料。\n\n請先使用「註冊」功能完成註冊。"
            )
            return
        
        # 取得當前使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示選擇要修改的欄位
        actions = [
            {
                "type": "postback",
                "label": "📱 手機號碼",
                "data": f"action=edit_profile&step=input&field=phone"
            },
            {
                "type": "postback",
                "label": "📍 地址",
                "data": f"action=edit_profile&step=input&field=address"
            },
            {
                "type": "postback",
                "label": "📧 Email",
                "data": f"action=edit_profile&step=input&field=email"
            },
            {
                "type": "postback",
                "label": "返回",
                "data": "action=view_profile&step=view"
            }
        ]
        
        # LINE 按鈕範本 text 欄位限制 60 字元，需要簡化顯示
        # 使用最簡潔的版本，只顯示關鍵提示
        current_info = "📋修改註冊資料\n\n請選擇要修改的欄位："
        
        try:
            response = self.message_service.send_buttons_template(
                reply_token,
                "修改註冊資料",
                current_info,
                actions
            )
            response.raise_for_status()  # 檢查 HTTP 狀態碼
        except requests.exceptions.RequestException as e:
            print(f"❌ 發送修改註冊資料選單失敗: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   回應內容：{e.response.text}")
            # 嘗試發送文字訊息作為備用
            backup_message = f"""📋 您目前的資料：

• 姓名：{user.full_name or '未填寫'}（不可修改）
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}

請點擊主選單中的「修改註冊資料」來修改資料。"""
            self.message_service.send_text(reply_token, backup_message)
    
    def handle_edit_profile_input(self, reply_token: str, user_id: str, text: str) -> None:
        """處理修改註冊資料輸入"""
        if not self.auth_service:
            return
        
        # 檢查是否在修改流程中
        if user_id not in self.edit_profile_states:
            return
        
        # 檢查是否要取消修改
        if text.strip().lower() in ['取消', 'cancel', '取消修改']:
            del self.edit_profile_states[user_id]
            self.message_service.send_text(
                reply_token,
                "❌ 已取消修改流程。"
            )
            return
        
        state = self.edit_profile_states[user_id]
        field = state.get('field')
        
        if field == 'phone':
            # 驗證並更新手機號碼
            phone = text.strip().replace('-', '').replace(' ', '')
            if not phone.isdigit() or len(phone) != 10 or not phone.startswith('09'):
                self.message_service.send_text(
                    reply_token,
                    "❌ 手機號碼格式不正確，請輸入10位數手機號碼（例如：0912345678）\n\n或輸入「取消」取消修改。"
                )
                return
            
            # 更新資料
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                updated_user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,  # 保持原姓名
                    phone=phone,
                    address=user.address,  # 保持原地址
                    email=user.email  # 保持原 Email
                )
                
                # 清除修改狀態
                del self.edit_profile_states[user_id]
                
                # 發送成功訊息並返回查看註冊資料頁面
                success_message = f"✅ 手機號碼已更新為：{phone}"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                del self.edit_profile_states[user_id]
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
        
        elif field == 'address':
            # 更新地址
            address = text.strip()
            if not address:
                self.message_service.send_text(
                    reply_token,
                    "❌ 地址不能為空，請重新輸入。\n\n或輸入「取消」取消修改。"
                )
                return
            
            # 更新資料
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                updated_user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,  # 保持原姓名
                    phone=user.phone,  # 保持原手機
                    address=address,
                    email=user.email  # 保持原 Email
                )
                
                # 清除修改狀態
                del self.edit_profile_states[user_id]
                
                # 發送成功訊息並返回查看註冊資料頁面
                success_message = f"✅ 地址已更新為：{address}"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                del self.edit_profile_states[user_id]
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
        
        elif field == 'email':
            # 更新 Email
            email = text.strip()
            if email.lower() in ['跳過', 'skip', '略過', '清除', '清空', '']:
                email = None
            else:
                # 簡單的 Email 驗證
                if '@' not in email or '.' not in email.split('@')[-1]:
                    self.message_service.send_text(
                        reply_token,
                        "❌ Email 格式不正確，請重新輸入或輸入「跳過」清除 Email。"
                    )
                    return
            
            # 更新資料
            user = self.auth_service.get_user_by_line_id(user_id)
            if user:
                updated_user = self.auth_service.create_line_user(
                    line_user_id=user_id,
                    full_name=user.full_name,  # 保持原姓名
                    phone=user.phone,  # 保持原手機
                    address=user.address,  # 保持原地址
                    email=email
                )
                
                # 清除修改狀態
                del self.edit_profile_states[user_id]
                
                # 發送成功訊息並返回查看註冊資料頁面
                if email:
                    success_message = f"✅ Email 已更新為：{email}"
                else:
                    success_message = "✅ Email 已清除。"
                self._send_update_success_and_show_profile(reply_token, user_id, success_message)
            else:
                del self.edit_profile_states[user_id]
                self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
    
    def _send_update_success_and_show_profile(self, reply_token: str, user_id: str, success_message: str) -> None:
        """發送更新成功訊息並顯示註冊資料頁面"""
        # 取得更新後的使用者資料
        user = self.auth_service.get_user_by_line_id(user_id) if self.auth_service else None
        if not user:
            # 如果無法取得使用者資料，只發送成功訊息
            self.message_service.send_text(reply_token, success_message)
            return
        
        # 顯示更新後的註冊資料
        user_info = f"""📋 您的註冊資料：

• 姓名：{user.full_name or '未填寫'}
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}"""
        
        # 準備操作按鈕
        actions = [
            {
                "type": "postback",
                "label": "✏️ 修改資料",
                "data": "action=edit_profile&step=select_field"
            },
            {
                "type": "postback",
                "label": "🗑️ 取消註冊",
                "data": "action=delete_registration&step=confirm"
            },
            {
                "type": "postback",
                "label": "返回主選單",
                "data": "action=job&step=menu"
            }
        ]
        
        # 使用 send_multiple_messages 在同一個回覆中發送成功訊息、更新後的資料和操作按鈕
        messages = [
            {
                "type": "text",
                "text": success_message
            },
            {
                "type": "text",
                "text": user_info
            },
            {
                "type": "template",
                "altText": "註冊資料操作",
                "template": {
                    "type": "buttons",
                    "title": "註冊資料",
                    "text": "請選擇操作：",
                    "actions": actions
                }
            }
        ]
        
        try:
            self.message_service.send_multiple_messages(reply_token, messages)
        except Exception as e:
            print(f"❌ 發送更新成功訊息和註冊資料失敗: {e}")
            # 如果發送失敗，至少發送成功訊息
            self.message_service.send_text(reply_token, success_message)
    
    def handle_delete_registration(self, reply_token: str, user_id: str) -> None:
        """處理取消註冊 - 顯示確認訊息"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 取消註冊功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無需取消。"
            )
            return
        
        # 取得使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示確認訊息（LINE 按鈕範本 text 限制 60 字元）
        # 使用簡潔版本
        confirm_text = "⚠️ 確認取消註冊\n\n取消後將無法報名工作，且無法復原。\n\n確定要取消嗎？"
        
        actions = [
            {
                "type": "postback",
                "label": "確認取消",
                "data": "action=delete_registration&step=confirm_delete"
            },
            {
                "type": "postback",
                "label": "返回",
                "data": "action=view_profile&step=view"
            }
        ]
        
        self.message_service.send_buttons_template(
            reply_token,
            "取消註冊",
            confirm_text,
            actions
        )
    
    def handle_confirm_delete_registration(self, reply_token: str, user_id: str) -> None:
        """處理確認取消註冊"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 取消註冊功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無需取消。"
            )
            return
        
        # 取消使用者註冊
        success = self.auth_service.delete_line_user(user_id)
        
        if success:
            # 同時取消該使用者的所有報名記錄
            applications = self.application_service.get_user_applications(user_id)
            for app in applications:
                self.application_service.cancel_application(user_id, app.job_id)
            
            self.message_service.send_text(
                reply_token,
                "✅ 您的註冊已成功取消。\n\n如需重新使用服務，請重新註冊。"
            )
        else:
            self.message_service.send_text(
                reply_token,
                "❌ 取消註冊失敗，請稍後再試或聯絡客服。"
            )
    
    def show_user_profile(self, reply_token: str, user_id: str) -> None:
        """顯示使用者註冊資料"""
        if not self.auth_service:
            self.message_service.send_text(reply_token, "❌ 查看註冊資料功能暫時無法使用。")
            return
        
        # 檢查是否已註冊
        if not self.auth_service.is_line_user_registered(user_id):
            self.message_service.send_text(
                reply_token,
                "❌ 您尚未註冊，無法查看註冊資料。\n\n請先使用「註冊」功能完成註冊。"
            )
            return
        
        # 取得使用者資料
        user = self.auth_service.get_user_by_line_id(user_id)
        if not user:
            self.message_service.send_text(reply_token, "❌ 找不到您的帳號資訊。")
            return
        
        # 顯示註冊資料（使用文字訊息，因為內容較長）
        user_info = f"""📋 您的註冊資料：

• 姓名：{user.full_name or '未填寫'}
• 手機：{user.phone or '未填寫'}
• 地址：{user.address or '未填寫'}
• Email：{user.email or '未填寫'}
• 註冊時間：{user.created_at}"""
        
        # 準備操作按鈕
        actions = [
            {
                "type": "postback",
                "label": "✏️ 修改資料",
                "data": "action=edit_profile&step=select_field"
            },
            {
                "type": "postback",
                "label": "🗑️ 取消註冊",
                "data": "action=delete_registration&step=confirm"
            },
            {
                "type": "postback",
                "label": "返回主選單",
                "data": "action=job&step=menu"
            }
        ]
        
        # 使用 send_multiple_messages 在同一個回覆中發送資料和按鈕
        messages = [
            {
                "type": "text",
                "text": user_info
            },
            {
                "type": "template",
                "altText": "註冊資料操作",
                "template": {
                    "type": "buttons",
                    "title": "註冊資料",
                    "text": "請選擇操作：",
                    "actions": actions
                }
            }
        ]
        
        try:
            self.message_service.send_multiple_messages(reply_token, messages)
        except Exception as e:
            print(f"❌ 發送註冊資料失敗: {e}")
            # 如果發送失敗，至少發送文字訊息
            self.message_service.send_text(reply_token, user_info)
    
    def show_main_menu(self, reply_token: str, user_id: Optional[str] = None) -> None:
        """顯示主選單"""
        # 檢查使用者是否已註冊
        is_registered = False
        if self.auth_service and user_id:
            is_registered = self.auth_service.is_line_user_registered(user_id)
        
        actions = []
        
        if not is_registered:
            # 未註冊使用者：顯示註冊選項
            actions.append({
                "type": "postback",
                "label": "📝 註冊",
                "data": "action=register&step=register"
            })
        
        actions.extend([
            {
                "type": "postback",
                "label": "查看工作列表",
                "data": "action=job&step=list"
            },
            {
                "type": "postback",
                "label": "查詢已報名",
                "data": "action=job&step=my_applications"
            }
        ])
        
        # 已註冊使用者：顯示查看註冊資料選項
        if is_registered:
            actions.append({
                "type": "postback",
                "label": "👤 查看註冊資料",
                "data": "action=view_profile&step=view"
            })
        
        actions.append({
            "type": "message",
            "label": "聯絡客服",
            "text": "我需要客服協助"
        })
        
        menu_text = "請選擇您需要的服務："
        if not is_registered:
            menu_text = "⚠️ 您尚未註冊，請先完成註冊才能報名工作。\n\n" + menu_text
        
        self.message_service.send_buttons_template(
            reply_token,
            "Good Job 報名系統",
            menu_text,
            actions
        )

# ==================== 模組 5: FastAPI 後台 API ====================

# 建立 FastAPI 應用程式
api_app = FastAPI(title="Good Job 報名系統 API", version="1.0.0")

# 全域服務實例（實際應用中應該使用依賴注入）
job_service = JobService()
application_service = ApplicationService()

# ==================== 認證相關 API ====================

@api_app.post("/api/auth/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate):
    """註冊新使用者"""
    try:
        user = auth_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"註冊失敗：{str(e)}")

@api_app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
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

@api_app.get("/api/auth/me", response_model=User)
def get_current_user_info(current_user: UserInDB = Depends(get_current_active_user)):
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

# ==================== 地理編碼 API ====================

class GeocodeRequest(BaseModel):
    """地理編碼請求"""
    address: str = Field(..., description="地址")

class GeocodeResponse(BaseModel):
    """地理編碼回應"""
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    success: bool
    message: Optional[str] = None

class ReverseGeocodeRequest(BaseModel):
    """反向地理編碼請求"""
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="經度")

class ReverseGeocodeResponse(BaseModel):
    """反向地理編碼回應"""
    latitude: float
    longitude: float
    address: Optional[str] = None
    success: bool
    message: Optional[str] = None

@api_app.post("/api/geocode", response_model=GeocodeResponse)
def geocode_address(
    request: GeocodeRequest,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """根據地址取得經緯度座標（需要認證）"""
    coordinates = geocoding_service.get_coordinates(request.address)
    
    if coordinates:
        latitude, longitude = coordinates
        return GeocodeResponse(
            address=request.address,
            latitude=latitude,
            longitude=longitude,
            success=True,
            message="成功取得座標"
        )
    else:
        return GeocodeResponse(
            address=request.address,
            latitude=None,
            longitude=None,
            success=False,
            message="無法取得座標，請檢查地址或 Google Maps API Key 設定"
        )

@api_app.post("/api/geocode/reverse", response_model=ReverseGeocodeResponse)
def reverse_geocode(
    request: ReverseGeocodeRequest,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """根據經緯度取得地址（反向地理編碼，需要認證）"""
    address = geocoding_service.get_address_from_coordinates(
        request.latitude,
        request.longitude
    )
    
    if address:
        return ReverseGeocodeResponse(
            latitude=request.latitude,
            longitude=request.longitude,
            address=address,
            success=True,
            message="成功取得地址"
        )
    else:
        return ReverseGeocodeResponse(
            latitude=request.latitude,
            longitude=request.longitude,
            address=None,
            success=False,
            message="無法取得地址，請檢查座標或 Google Maps API Key 設定"
        )

# ==================== 工作管理 API（需要認證） ====================

@api_app.post("/api/jobs", response_model=Job, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: CreateJobRequest,
    current_user: UserInDB = Depends(require_admin)
):
    """建立新工作（需要管理員權限）"""
    try:
        job = job_service.create_job(job_data)
        return job
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_app.get("/api/jobs", response_model=List[Job])
def get_all_jobs(current_user: UserInDB = Depends(get_current_active_user)):
    """取得所有工作（需要認證）"""
    return job_service.get_all_jobs()

@api_app.get("/api/jobs/{job_id}", response_model=Job)
def get_job(
    job_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """取得特定工作（需要認證）"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="工作不存在")
    return job

@api_app.get("/api/jobs/{job_id}/applications", response_model=List[Application])
def get_job_applications(
    job_id: str,
    current_user: UserInDB = Depends(require_admin)
):
    """取得工作的報名清單（需要管理員權限）"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="工作不存在")
    
    applications = application_service.get_job_applications(job_id)
    return applications

@api_app.get("/api/applications", response_model=List[Application])
def get_all_applications(current_user: UserInDB = Depends(require_admin)):
    """取得所有報名記錄（需要管理員權限）"""
    return list(application_service.applications.values())

# ==================== 使用者管理 API（需要管理員權限） ====================

@api_app.get("/api/users", response_model=List[User])
def get_all_users(current_user: UserInDB = Depends(require_admin)):
    """取得所有使用者列表（需要管理員權限）"""
    users = []
    for user_in_db in auth_service.users.values():
        users.append(User(
            id=user_in_db.id,
            username=user_in_db.username,
            email=user_in_db.email,
            full_name=user_in_db.full_name,
            phone=user_in_db.phone,
            address=user_in_db.address,
            is_admin=user_in_db.is_admin,
            is_active=user_in_db.is_active,
            created_at=user_in_db.created_at,
            line_user_id=user_in_db.line_user_id
        ))
    return users

@api_app.get("/api/users/{username}", response_model=User)
def get_user(
    username: str,
    current_user: UserInDB = Depends(require_admin)
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
        phone=user.phone,
        address=user.address,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        line_user_id=user.line_user_id
    )

# ==================== 模組 6: LINE Bot 主應用程式 ====================

class PartTimeJobBot:
    """Good Job 報名系統主應用程式"""
    
    def __init__(self, channel_access_token: str, channel_secret: Optional[str] = None, auth_service: Optional[AuthService] = None):
        # 初始化服務
        self.job_service = job_service
        self.application_service = application_service
        self.message_service = LineMessageService(channel_access_token)
        self.handler = JobHandler(self.job_service, self.application_service, self.message_service, auth_service)
        self.channel_secret = channel_secret
        
        # 建立 Flask 應用程式（用於 LINE Webhook）
        self.flask_app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """設定路由"""
        @self.flask_app.route("/", methods=['POST'])
        def webhook():
            return self.handle_webhook()
    
    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """
        驗證 LINE Webhook 請求簽名
        
        參數:
            body: 請求原始 body（bytes）
            signature: X-Line-Signature header 的值
        
        返回:
            bool: 驗證是否通過
        """
        if not self.channel_secret:
            # 如果沒有設定 channel_secret，跳過驗證（開發模式）
            print("⚠️  警告：未設定 Channel Secret，跳過簽名驗證")
            return True
        
        try:
            # 使用 Channel Secret 和請求體計算 HMAC-SHA256
            hash_value = hmac.new(
                self.channel_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).digest()
            
            # 轉換為 base64
            expected_signature = base64.b64encode(hash_value).decode('utf-8')
            
            # 比較簽名（使用安全比較避免時間攻擊）
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            print(f"❌ 簽名驗證錯誤：{e}")
            return False
    
    def handle_webhook(self):
        """處理 LINE Webhook"""
        try:
            # 驗證請求簽名
            signature = request.headers.get('X-Line-Signature', '')
            body = request.get_data()
            
            if not self._verify_signature(body, signature):
                print(f"❌ Webhook 簽名驗證失敗")
                print(f"   收到的簽名：{signature[:20]}...")
                return 'Forbidden', 403
            
            # 解析 JSON 資料
            data = request.get_json()
            
            # 印出接收到的資料（方便除錯）
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 處理不同類型的事件
            for event in data.get('events', []):
                try:
                    event_type = event.get('type')
                    reply_token = event.get('replyToken')
                    user_id = event['source'].get('userId', 'unknown')
                    
                    if event_type == 'message':
                        self._handle_message(event, reply_token, user_id)
                    elif event_type == 'postback':
                        self._handle_postback(event, reply_token, user_id)
                except Exception as e:
                    print(f"❌ 處理事件時發生錯誤：{e}")
                    import traceback
                    traceback.print_exc()
                    # 嘗試發送錯誤訊息給使用者
                    try:
                        if reply_token:
                            self.message_service.send_text(
                                reply_token,
                                "❌ 處理您的請求時發生錯誤，請稍後再試。"
                            )
                    except:
                        pass
            
            return 'OK', 200
        except Exception as e:
            print(f"❌ Webhook 處理錯誤：{e}")
            import traceback
            traceback.print_exc()
            return 'OK', 200  # 即使出錯也返回 OK，避免 LINE 重試
    
    def _handle_message(self, event: Dict, reply_token: str, user_id: str) -> None:
        """處理文字訊息"""
        message_text = event['message'].get('text', '')
        
        # 檢查是否在註冊流程中
        if user_id in self.handler.registration_states:
            # 如果輸入的是 menu 相關指令，先清除註冊狀態，然後顯示主選單
            if message_text.strip().lower() in ['選單', 'menu', 'menus', 'Menu', 'MENU', '工作', 'jobs']:
                # 清除註冊狀態
                if user_id in self.handler.registration_states:
                    del self.handler.registration_states[user_id]
                self.handler.show_main_menu(reply_token, user_id)
                return
            # 其他情況正常處理註冊輸入
            self.handler.handle_register_input(reply_token, user_id, message_text)
            return
        
        # 檢查是否在修改資料流程中
        if user_id in self.handler.edit_profile_states:
            # 如果輸入的是 menu 相關指令，先清除修改狀態，然後顯示主選單
            if message_text.strip().lower() in ['選單', 'menu', 'menus', 'Menu', 'MENU', '工作', 'jobs']:
                # 清除修改狀態
                if user_id in self.handler.edit_profile_states:
                    del self.handler.edit_profile_states[user_id]
                self.handler.show_main_menu(reply_token, user_id)
                return
            # 其他情況正常處理修改輸入
            self.handler.handle_edit_profile_input(reply_token, user_id, message_text)
            return
        
        if message_text in ['選單', 'menu', 'Menu', 'MENU', '工作', 'jobs']:
            self.handler.show_main_menu(reply_token, user_id)
        elif message_text in ['工作列表', '查看工作', 'list']:
            self.handler.show_available_jobs(reply_token, user_id)
        elif message_text in ['已報名', '我的報名', '報名記錄', 'my_applications']:
            self.handler.show_user_applications(reply_token, user_id)
        elif message_text in ['註冊', 'register', 'Register', 'REGISTER']:
            self.handler.handle_register(reply_token, user_id)
        else:
            # 預設顯示主選單
            self.handler.show_main_menu(reply_token, user_id)
    
    def _handle_postback(self, event: Dict, reply_token: str, user_id: str) -> None:
        """處理 postback 事件"""
        postback_data = event['postback'].get('data', '')
        print(f"收到 postback: {postback_data}")
        
        # 解析 postback data
        parsed_data = urllib.parse.parse_qs(postback_data)
        action = parsed_data.get('action', [''])[0]
        step = parsed_data.get('step', [''])[0]
        job_id = parsed_data.get('job_id', [''])[0]
        shift = parsed_data.get('shift', [''])[0]
        
        # 解碼 shift（如果有）
        if shift:
            shift = urllib.parse.unquote(shift)
        
        # 根據不同的步驟處理
        if action == 'register':
            if step == 'register':
                self.handler.handle_register(reply_token, user_id)
        elif action == 'edit_profile':
            if step == 'select_field':
                self.handler.handle_edit_profile(reply_token, user_id)
            elif step == 'input':
                field = parsed_data.get('field', [''])[0]
                if field:
                    # 設定修改狀態並提示輸入
                    self.handler.edit_profile_states[user_id] = {'field': field}
                    user = self.handler.auth_service.get_user_by_line_id(user_id) if self.handler.auth_service else None
                    
                    if field == 'phone':
                        current = user.phone if user and user.phone else '未填寫'
                        prompt = f"📱 修改手機號碼\n\n目前的手機號碼：{current}\n\n請輸入新的手機號碼（格式：09XX-XXX-XXX 或 09XXXXXXXX）：\n\n或輸入「取消」取消修改。"
                    elif field == 'address':
                        current = user.address if user and user.address else '未填寫'
                        prompt = f"📍 修改地址\n\n目前的地址：{current}\n\n請輸入新的地址：\n\n或輸入「取消」取消修改。"
                    elif field == 'email':
                        current = user.email if user and user.email else '未填寫'
                        prompt = f"📧 修改 Email\n\n目前的 Email：{current}\n\n請輸入新的 Email：\n\n（可選，輸入「跳過」可清除 Email）\n或輸入「取消」取消修改。"
                    else:
                        prompt = "請輸入新值："
                    
                    self.handler.message_service.send_text(reply_token, prompt)
        elif action == 'view_profile':
            if step == 'view':
                self.handler.show_user_profile(reply_token, user_id)
        elif action == 'delete_registration':
            if step == 'confirm':
                self.handler.handle_delete_registration(reply_token, user_id)
            elif step == 'confirm_delete':
                self.handler.handle_confirm_delete_registration(reply_token, user_id)
        elif action == 'job':
            if step == 'list':
                self.handler.show_available_jobs(reply_token, user_id)
            elif step == 'detail':
                if job_id:
                    self.handler.show_job_detail(reply_token, user_id, job_id)
            elif step == 'apply':
                if job_id:
                    self.handler.handle_apply_job(reply_token, user_id, job_id)
            elif step == 'select_shift':
                if job_id and shift:
                    self.handler.handle_select_shift(reply_token, user_id, job_id, shift)
            elif step == 'cancel':
                if job_id:
                    self.handler.handle_cancel_application(reply_token, user_id, job_id)
            elif step == 'confirm_cancel':
                if job_id:
                    self.handler.handle_confirm_cancel(reply_token, user_id, job_id)
            elif step == 'my_applications':
                self.handler.show_user_applications(reply_token, user_id)
            elif step == 'menu':
                self.handler.show_main_menu(reply_token, user_id)
    
    def run(self, port: int = 3000, debug: bool = False, use_threading: bool = True):
        """
        啟動伺服器
        
        參數:
            port: 連接埠號
            debug: 是否啟用除錯模式
            use_threading: 是否使用執行緒在背景執行
        """
        if use_threading:
            import threading
            def run_server():
                self.flask_app.run(port=port, debug=debug, use_reloader=False, use_debugger=False)
            
            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            print(f"✅ LINE Bot 伺服器已在背景啟動，監聽 port {port}")
            print("⚠️  注意：在 Jupyter 中，伺服器會在背景執行")
            print("   要停止伺服器，請重新啟動 kernel")
        else:
            self.flask_app.run(port=port, debug=debug)

# ==================== 測試資料建立 ====================

def create_sample_jobs(job_service: JobService):
    """建立測試工作資料"""
    from datetime import date, timedelta
    
    # 檢查是否已有工作
    if len(job_service.jobs) > 0:
        print("ℹ️  已有工作資料，跳過建立測試資料")
        return
    
    # 建立幾個測試工作
    sample_jobs = [
        {
            "name": "餐廳服務員",
            "location": "台北市信義區信義路五段7號",
            "date": (date.today() + timedelta(days=3)).strftime('%Y-%m-%d'),
            "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
            "location_image_url": None
        },
        {
            "name": "活動工作人員",
            "location": "桃園市桃園區中正五街196號",
            "date": (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "shifts": ["早班:09-18", "晚班:18-22"],
            "location_image_url": None
        },
        {
            "name": "展覽導覽員",
            "location": "新北市鶯歌區鳳吉一街193號",
            "date": (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            "shifts": ["早班:10-18"],
            "location_image_url": None
        }
    ]
    
    for job_data in sample_jobs:
        job_request = CreateJobRequest(**job_data)
        job = job_service.create_job(job_request)
        print(f"✅ 已建立測試工作：{job.name} (ID: {job.id})")
    
    print(f"✅ 共建立 {len(sample_jobs)} 個測試工作")

# ==================== 主程式 ====================

# Channel Secret 用於驗證 Webhook 請求來源（從 LINE Developers Console 取得）
# 如果未設定，系統會跳過簽名驗證（僅用於開發測試）
LINE_CHANNEL_ACCESS_TOKEN = "oZPbAQXckPCTbRPN67GNPlyG/MqToO3haMOIvWOI35PGg8ZdBYEVtOc1KdJ+zYLJjOJ8+/YGaEk4f7m6W1RavpsYIp+5k1taVZ47HYboydFvMbTQ4rxXlNGysl2q0sM79gbzVuGnzHkPL2mf9SfU1gdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "793a80c83472d9ddf0451cad2dd4077c"
#
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", LINE_CHANNEL_ACCESS_TOKEN)
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", LINE_CHANNEL_SECRET)

# Google Maps API Key（從環境變數或使用預設值）
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyDqcXhRP7pJmQIlO_F86Oh8lSmEtOUgXaw")

# 重新初始化 Geocoding 服務以使用正確的 API Key
geocoding_service = GeocodingService(default_api_key=GOOGLE_MAPS_API_KEY)

# 建立測試資料（在模組層級建立，每個進程都會執行，但有檢查機制避免重複）
create_sample_jobs(job_service)

# 建立 Bot 實例（在模組層級建立，每個進程都需要自己的實例）
bot = PartTimeJobBot(CHANNEL_ACCESS_TOKEN, channel_secret=CHANNEL_SECRET, auth_service=auth_service)

# 如果直接執行此檔案，啟動伺服器
if __name__ == "__main__":
    
    # 檢查 port 是否已被佔用
    def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
        """檢查指定 port 是否已被使用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return False
            except OSError:
                return True
    
    # 檢查是否在主進程中（Flask reloader 會產生子進程）
    # WERKZEUG_RUN_MAIN 在 reloader 子進程中會被設為 'true'
    is_main_process = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'
    
    # 啟動 FastAPI（後台 API）- 只在主進程且 port 未被佔用時啟動
    def run_fastapi():
        try:
            uvicorn.run(api_app, host="0.0.0.0", port=8880)
        except Exception as e:
            print(f"⚠️  FastAPI 啟動失敗：{e}")
    
    # 啟動 LINE Bot（前台）
    def run_line_bot():
        bot.run(port=3000, debug=True, use_threading=False)
    
    # 只在主進程且 port 未被佔用時啟動 FastAPI
    if is_main_process and not is_port_in_use(8880):
        fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
        fastapi_thread.start()
        print("✅ FastAPI 伺服器已啟動，監聽 http://0.0.0.0:8880")
        print("   API 文件：http://localhost:8880/docs")
    elif is_port_in_use(8880) and is_main_process:
        print("ℹ️  FastAPI 伺服器已在運行（port 8880 已被佔用）")
    
    # 在前景執行 LINE Bot
    print("✅ 啟動 LINE Bot 伺服器...")
    run_line_bot()
