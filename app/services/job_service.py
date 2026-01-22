"""
工作管理服務
"""
from typing import List, Optional
import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.job import JobModel
from app.models.schemas import Job, CreateJobRequest
from app.services.geocoding_service import GeocodingService


class JobService:
    """工作管理服務"""
    
    def __init__(self, db: Optional[Session] = None, geocoding_service: Optional[GeocodingService] = None):
        """
        初始化工作服務
        
        參數:
            db: 資料庫會話（可選，如果提供則使用，否則創建新會話）
            geocoding_service: 地理編碼服務（可選）
        """
        self.db = db
        self.geocoding_service = geocoding_service
    
    def _get_db(self) -> Session:
        """取得資料庫會話"""
        if self.db:
            return self.db
        return SessionLocal()
    
    def _get_next_job_id(self, db: Optional[Session] = None) -> str:
        """
        取得下一個工作編號
        
        參數:
            db: 資料庫會話（可選）
        
        返回:
            str: 工作編號（格式：JOB001, JOB002, ...）
        """
        if db is None:
            db = self._get_db()
        
        # 從資料庫查詢最大流水號
        max_job = db.query(JobModel).filter(JobModel.id.like('JOB%')).order_by(JobModel.id.desc()).first()
        
        if max_job:
            try:
                # 提取流水號部分（JOB001 -> 001 -> 1）
                sequence = int(max_job.id[3:])
                next_sequence = sequence + 1
            except ValueError:
                next_sequence = 1
        else:
            next_sequence = 1
        
        # 使用 3 位數流水號，不足補零
        return f"JOB{next_sequence:03d}"
    
    def create_job(self, job_data: CreateJobRequest, db: Optional[Session] = None) -> Job:
        """
        建立工作
        
        參數:
            job_data: 工作資料
            db: 資料庫會話（可選）
        
        返回:
            Job: 建立的工作物件
        """
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            # 工作編號格式：JOB+流水號（例如：JOB001, JOB002）
            job_id = self._get_next_job_id(db)
            
            # 取得座標（如果未提供）
            latitude = job_data.latitude
            longitude = job_data.longitude
            
            if (latitude is None or longitude is None) and self.geocoding_service:
                # 嘗試從地址取得座標
                coordinates = self.geocoding_service.get_coordinates(job_data.location)
                if coordinates:
                    latitude, longitude = coordinates
                else:
                    print(f"⚠️  無法取得工作地點座標：{job_data.location}")
            
            # 建立資料庫記錄
            job_model = JobModel(
                id=job_id,
                name=job_data.name,
                location=job_data.location,
                date=job_data.date,
                shifts=job_data.shifts,
                location_image_url=job_data.location_image_url,
                latitude=latitude,
                longitude=longitude
            )
            
            db.add(job_model)
            db.commit()
            db.refresh(job_model)
            
            # 轉換為 Pydantic 模型
            job = Job(
                id=job_model.id,
                name=job_model.name,
                location=job_model.location,
                date=job_model.date,
                shifts=job_model.shifts,
                location_image_url=job_model.location_image_url,
                latitude=job_model.latitude,
                longitude=job_model.longitude
            )
            
            return job
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if should_close:
                db.close()
    
    def get_job(self, job_id: str, db: Optional[Session] = None) -> Optional[Job]:
        """取得工作"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            job_model = db.query(JobModel).filter(JobModel.id == job_id).first()
            if not job_model:
                return None
            
            return Job(
                id=job_model.id,
                name=job_model.name,
                location=job_model.location,
                date=job_model.date,
                shifts=job_model.shifts,
                location_image_url=job_model.location_image_url,
                latitude=job_model.latitude,
                longitude=job_model.longitude
            )
        finally:
            if should_close:
                db.close()
    
    def get_all_jobs(self, db: Optional[Session] = None) -> List[Job]:
        """取得所有工作"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            job_models = db.query(JobModel).order_by(JobModel.date).all()
            return [
                Job(
                    id=job.id,
                    name=job.name,
                    location=job.location,
                    date=job.date,
                    shifts=job.shifts,
                    location_image_url=job.location_image_url,
                    latitude=job.latitude,
                    longitude=job.longitude
                )
                for job in job_models
            ]
        finally:
            if should_close:
                db.close()
    
    def get_available_jobs(self, db: Optional[Session] = None) -> List[Job]:
        """取得可報班的工作（日期大於等於今天）"""
        if db is None:
            db = self._get_db()
            should_close = True
        else:
            should_close = False
        
        try:
            today = datetime.date.today().strftime('%Y-%m-%d')
            job_models = db.query(JobModel).filter(JobModel.date >= today).order_by(JobModel.date).all()
            
            return [
                Job(
                    id=job.id,
                    name=job.name,
                    location=job.location,
                    date=job.date,
                    shifts=job.shifts,
                    location_image_url=job.location_image_url,
                    latitude=job.latitude,
                    longitude=job.longitude
                )
                for job in job_models
            ]
        finally:
            if should_close:
                db.close()
