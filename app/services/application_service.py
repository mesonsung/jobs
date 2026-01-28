"""
報班管理服務
"""
from typing import List, Optional, Tuple
import datetime
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import SessionLocal
from app.core.time_utils import utc_now
from app.models.job import ApplicationModel
from app.models.schemas import Application


class ApplicationService:
    """報班管理服務"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化報班服務
        
        參數:
            db: 資料庫會話（可選，如果提供則使用，否則創建新會話）
        """
        self.db = db
    
    def _get_db(self) -> Session:
        """取得資料庫會話"""
        if self.db:
            return self.db
        return SessionLocal()
    
    def create_application(self, job_id: str, user_id: str, shift: str, user_name: Optional[str] = None, db: Optional[Session] = None) -> Application:
        """
        建立報班記錄
        
        參數:
            job_id: 工作ID
            user_id: 使用者ID
            shift: 選擇的班別
            user_name: 使用者名稱（可選）
            db: 資料庫會話（可選）
        
        返回:
            Application: 報班記錄
        """
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            # 報班編號格式：工作編號-日期-流水號
            # 例如：JOB001-20260110-001
            
            # 取得當前 UTC 日期（YYYYMMDD 格式，供編號與同一天篩選）
            _now = utc_now()
            today = _now.strftime('%Y%m%d')
            today_date = _now.date()
            
            # 計算該工作在同一天的流水號
            # 從資料庫查詢該工作在同一天的所有報班記錄
            same_day_count = db.query(ApplicationModel).filter(
                ApplicationModel.job_id == job_id,
                func.date(ApplicationModel.applied_at) == today_date
            ).count()
            
            # 流水號 = 當天報班數量 + 1（3位數，補零）
            sequence_number = same_day_count + 1
            sequence_str = f"{sequence_number:03d}"
            
            # 組合報班編號：工作編號-日期-流水號
            application_id = f"{job_id}-{today}-{sequence_str}"
            
            applied_at = utc_now()
            
            # 建立資料庫記錄
            application_model = ApplicationModel(
                id=application_id,
                job_id=job_id,
                user_id=user_id,
                user_name=user_name,
                shift=shift,
                applied_at=applied_at
            )
            
            db.add(application_model)
            db.commit()
            db.refresh(application_model)
            
            # 轉換為 Pydantic 模型
            application = Application(
                id=application_model.id,
                job_id=application_model.job_id,
                user_id=application_model.user_id,
                user_name=application_model.user_name,
                shift=application_model.shift,
                applied_at=application_model.applied_at.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            return application
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if should_close:
                db.close()
    
    def get_user_application_for_job(self, user_id: str, job_id: str, db: Optional[Session] = None) -> Optional[Application]:
        """取得使用者對特定工作的報班記錄"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            app_model = db.query(ApplicationModel).filter(
                ApplicationModel.user_id == user_id,
                ApplicationModel.job_id == job_id
            ).first()
            
            if not app_model:
                return None
            
            return Application(
                id=app_model.id,
                job_id=app_model.job_id,
                user_id=app_model.user_id,
                user_name=app_model.user_name,
                shift=app_model.shift,
                applied_at=app_model.applied_at.strftime('%Y-%m-%d %H:%M:%S')
            )
        finally:
            if should_close:
                db.close()
    
    def cancel_application(self, user_id: str, job_id: str, db: Optional[Session] = None) -> Tuple[bool, Optional[Application]]:
        """
        取消報班
        
        參數:
            user_id: 使用者ID
            job_id: 工作ID
            db: 資料庫會話（可選）
        
        返回:
            tuple: (是否成功, 取消的報班記錄)
        """
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            app_model = db.query(ApplicationModel).filter(
                ApplicationModel.user_id == user_id,
                ApplicationModel.job_id == job_id
            ).first()
            
            if not app_model:
                return False, None
            
            # 轉換為 Pydantic 模型（在刪除前）
            application = Application(
                id=app_model.id,
                job_id=app_model.job_id,
                user_id=app_model.user_id,
                user_name=app_model.user_name,
                shift=app_model.shift,
                applied_at=app_model.applied_at.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # 從資料庫刪除
            db.delete(app_model)
            db.commit()
            
            return True, application
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if should_close:
                db.close()
    
    def get_job_applications(self, job_id: str, db: Optional[Session] = None) -> List[Application]:
        """取得工作的所有報班記錄"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            app_models = db.query(ApplicationModel).filter(
                ApplicationModel.job_id == job_id
            ).order_by(ApplicationModel.applied_at.desc()).all()
            
            return [
                Application(
                    id=app.id,
                    job_id=app.job_id,
                    user_id=app.user_id,
                    user_name=app.user_name,
                    shift=app.shift,
                    applied_at=app.applied_at.strftime('%Y-%m-%d %H:%M:%S')
                )
                for app in app_models
            ]
        finally:
            if should_close:
                db.close()
    
    def get_user_applications(self, user_id: str, db: Optional[Session] = None) -> List[Application]:
        """
        取得使用者的所有報班記錄
        
        參數:
            user_id: 使用者ID
            db: 資料庫會話（可選）
        
        返回:
            list: 報班記錄列表
        """
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            app_models = db.query(ApplicationModel).filter(
                ApplicationModel.user_id == user_id
            ).order_by(ApplicationModel.applied_at.desc()).all()
            
            return [
                Application(
                    id=app.id,
                    job_id=app.job_id,
                    user_id=app.user_id,
                    user_name=app.user_name,
                    shift=app.shift,
                    applied_at=app.applied_at.strftime('%Y-%m-%d %H:%M:%S')
                )
                for app in app_models
            ]
        finally:
            if should_close:
                db.close()
