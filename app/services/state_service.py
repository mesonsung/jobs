"""
狀態管理服務
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.core.database import SessionLocal
from app.core.logger import setup_logger
from app.models.state import RegistrationStateModel, StateType

# 設置 logger
logger = setup_logger(__name__)


class StateService:
    """狀態管理服務"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化狀態服務
        
        參數:
            db: 資料庫會話（可選，如果提供則使用，否則創建新會話）
        """
        self.db = db
    
    def _get_db(self) -> Session:
        """取得資料庫會話"""
        if self.db:
            return self.db
        return SessionLocal()
    
    def get_registration_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        取得註冊流程狀態
        
        參數:
            user_id: LINE User ID
        
        返回:
            狀態字典，包含 'step' 和 'data'，如果不存在則返回 None
        """
        db = self._get_db()
        should_close = self.db is None
        
        try:
            state_model = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.user_id == user_id,
                RegistrationStateModel.state_type == StateType.REGISTRATION
            ).first()
            
            if not state_model:
                logger.debug(f"get_registration_state: user_id: {user_id} 沒有找到狀態")
                return None
            
            state = {
                'step': state_model.step,
                'data': state_model.get_data_dict()
            }
            logger.debug(f"get_registration_state: user_id: {user_id}, state: {state}")
            return state
        except Exception as e:
            logger.error(f"取得註冊狀態失敗：{e}", exc_info=True)
            return None
        finally:
            if should_close:
                db.close()
    
    def new_registration_state(self, user_id: str, step: str = 'name', data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        建立新的註冊流程狀態
        
        參數:
            user_id: LINE User ID
            step: 初始步驟（預設為 'name'）
            data: 初始資料（預設為空字典）
        
        返回:
            狀態字典
        """
        db = self._get_db()
        should_close = self.db is None
        
        try:
            # 檢查是否已存在狀態
            existing_state = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.user_id == user_id,
                RegistrationStateModel.state_type == StateType.REGISTRATION
            ).first()
            
            if existing_state:
                # 更新現有狀態
                existing_state.step = step
                existing_state.set_data_dict(data or {})
                existing_state.updated_at = func.now()
                db.commit()
                db.refresh(existing_state)
                logger.debug(f"new_registration_state: 更新現有狀態 user_id: {user_id}")
            else:
                # 建立新狀態
                state_model = RegistrationStateModel(
                    user_id=user_id,
                    state_type=StateType.REGISTRATION,
                    step=step,
                    data=None
                )
                state_model.set_data_dict(data or {})
                db.add(state_model)
                db.commit()
                db.refresh(state_model)
                logger.debug(f"new_registration_state: 建立新狀態 user_id: {user_id}")
            
            return {
                'step': step,
                'data': data or {}
            }
        except Exception as e:
            logger.error(f"建立註冊狀態失敗：{e}", exc_info=True)
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def update_registration_state(self, user_id: str, step: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新註冊流程狀態
        
        參數:
            user_id: LINE User ID
            step: 要更新的步驟（可選）
            data: 要更新的資料（可選）
        
        返回:
            是否更新成功
        """
        db = self._get_db()
        should_close = self.db is None
        
        try:
            state_model = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.user_id == user_id,
                RegistrationStateModel.state_type == StateType.REGISTRATION
            ).first()
            
            if not state_model:
                logger.warning(f"update_registration_state: user_id: {user_id} 沒有找到狀態")
                return False
            
            if step is not None:
                state_model.step = step
            if data is not None:
                state_model.set_data_dict(data)
            
            db.commit()
            db.refresh(state_model)
            logger.debug(f"update_registration_state: user_id: {user_id}, step: {step}, data: {data}")
            return True
        except Exception as e:
            logger.error(f"更新註冊狀態失敗：{e}", exc_info=True)
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    def delete_registration_state(self, user_id: str) -> bool:
        """
        刪除註冊流程狀態
        
        參數:
            user_id: LINE User ID
        
        返回:
            是否刪除成功
        """
        db = self._get_db()
        should_close = self.db is None
        
        try:
            state_model = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.user_id == user_id,
                RegistrationStateModel.state_type == StateType.REGISTRATION
            ).first()
            
            if state_model:
                db.delete(state_model)
                db.commit()
                logger.debug(f"delete_registration_state: user_id: {user_id} 狀態已刪除")
                return True
            else:
                logger.debug(f"delete_registration_state: user_id: {user_id} 沒有找到狀態")
                return False
        except Exception as e:
            logger.error(f"刪除註冊狀態失敗：{e}", exc_info=True)
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    def get_edit_profile_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        取得編輯資料流程狀態
        
        參數:
            user_id: LINE User ID
        
        返回:
            狀態字典，包含 'field'，如果不存在則返回 None
        """
        db = self._get_db()
        should_close = self.db is None
        
        try:
            state_model = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.user_id == user_id,
                RegistrationStateModel.state_type == StateType.EDIT_PROFILE
            ).first()
            
            if not state_model:
                logger.debug(f"get_edit_profile_state: user_id: {user_id} 沒有找到狀態")
                return None
            
            state = state_model.get_data_dict()
            logger.debug(f"get_edit_profile_state: user_id: {user_id}, state: {state}")
            return state
        except Exception as e:
            logger.error(f"取得編輯資料狀態失敗：{e}", exc_info=True)
            return None
        finally:
            if should_close:
                db.close()
    
    def new_edit_profile_state(self, user_id: str, field: str) -> Dict[str, Any]:
        """
        建立新的編輯資料流程狀態
        
        參數:
            user_id: LINE User ID
            field: 要編輯的欄位名稱
        
        返回:
            狀態字典
        """
        db = self._get_db()
        should_close = self.db is None
        
        try:
            # 檢查是否已存在狀態
            existing_state = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.user_id == user_id,
                RegistrationStateModel.state_type == StateType.EDIT_PROFILE
            ).first()
            
            data = {'field': field}
            
            if existing_state:
                # 更新現有狀態
                existing_state.set_data_dict(data)
                existing_state.updated_at = func.now()
                db.commit()
                db.refresh(existing_state)
                logger.debug(f"new_edit_profile_state: 更新現有狀態 user_id: {user_id}")
            else:
                # 建立新狀態
                state_model = RegistrationStateModel(
                    user_id=user_id,
                    state_type=StateType.EDIT_PROFILE,
                    step='input',  # 編輯流程固定為 input 步驟
                    data=None
                )
                state_model.set_data_dict(data)
                db.add(state_model)
                db.commit()
                db.refresh(state_model)
                logger.debug(f"new_edit_profile_state: 建立新狀態 user_id: {user_id}")
            
            return data
        except Exception as e:
            logger.error(f"建立編輯資料狀態失敗：{e}", exc_info=True)
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def delete_edit_profile_state(self, user_id: str) -> bool:
        """
        刪除編輯資料流程狀態
        
        參數:
            user_id: LINE User ID
        
        返回:
            是否刪除成功
        """
        db = self._get_db()
        should_close = self.db is None
        
        try:
            state_model = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.user_id == user_id,
                RegistrationStateModel.state_type == StateType.EDIT_PROFILE
            ).first()
            
            if state_model:
                db.delete(state_model)
                db.commit()
                logger.debug(f"delete_edit_profile_state: user_id: {user_id} 狀態已刪除")
                return True
            else:
                logger.debug(f"delete_edit_profile_state: user_id: {user_id} 沒有找到狀態")
                return False
        except Exception as e:
            logger.error(f"刪除編輯資料狀態失敗：{e}", exc_info=True)
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    def cleanup_expired_states(self, hours: int = 24) -> int:
        """
        清理過期的狀態（超過指定小時未更新的狀態）
        
        參數:
            hours: 過期時間（小時）
        
        返回:
            清理的狀態數量
        """
        from datetime import datetime, timedelta
        from sqlalchemy import and_
        
        db = self._get_db()
        should_close = self.db is None
        
        try:
            expire_time = datetime.now() - timedelta(hours=hours)
            
            expired_states = db.query(RegistrationStateModel).filter(
                RegistrationStateModel.updated_at < expire_time
            ).all()
            
            count = len(expired_states)
            for state in expired_states:
                db.delete(state)
            
            db.commit()
            logger.info(f"清理了 {count} 個過期狀態（超過 {hours} 小時未更新）")
            return count
        except Exception as e:
            logger.error(f"清理過期狀態失敗：{e}", exc_info=True)
            db.rollback()
            return 0
        finally:
            if should_close:
                db.close()
