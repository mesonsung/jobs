"""
狀態管理相關資料模型
"""
from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum
import json
from enum import Enum
from app.core.database import Base
from app.core.time_utils import utc_now


class StateType(str, Enum):
    """狀態類型枚舉"""
    REGISTRATION = "registration"  # 註冊流程狀態
    EDIT_PROFILE = "edit_profile"  # 編輯資料狀態


class RegistrationStateModel(Base):
    """註冊和編輯流程狀態資料表模型"""
    __tablename__ = "registration_states"
    
    user_id = Column(String, primary_key=True, index=True)  # LINE User ID
    state_type = Column(SQLEnum(StateType), nullable=False, index=True)  # 狀態類型
    step = Column(String, nullable=False)  # 當前步驟
    data = Column(Text, nullable=True)  # 狀態資料（JSON 字串）
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    def get_data_dict(self) -> dict:
        """將 JSON 字串轉換為字典"""
        if not self.data:
            return {}
        try:
            return json.loads(self.data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_data_dict(self, data: dict) -> None:
        """將字典轉換為 JSON 字串並儲存"""
        if data:
            self.data = json.dumps(data, ensure_ascii=False)
        else:
            self.data = None
