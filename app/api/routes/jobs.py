"""
工作管理相關 API 路由
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from app.services.job_service import JobService
from app.services.application_service import ApplicationService
from app.models.schemas import Job, Application, CreateJobRequest
from app.api.dependencies import get_current_active_user, require_admin
from app.models.schemas import UserInDB
from typing import Annotated

router = APIRouter(prefix="/api/jobs", tags=["工作管理"])

# 創建服務實例（單例模式）
_job_service_instance = None
_application_service_instance = None

def get_job_service() -> JobService:
    """取得 JobService 實例"""
    global _job_service_instance
    if _job_service_instance is None:
        from app.services.geocoding_service import GeocodingService
        from app.config import GOOGLE_MAPS_API_KEY
        geocoding_service = GeocodingService(api_key=GOOGLE_MAPS_API_KEY)
        _job_service_instance = JobService(geocoding_service=geocoding_service)
    return _job_service_instance

def get_application_service() -> ApplicationService:
    """取得 ApplicationService 實例"""
    global _application_service_instance
    if _application_service_instance is None:
        _application_service_instance = ApplicationService()
    return _application_service_instance


@router.post("", response_model=Job, status_code=201)
def create_job(
    job_data: CreateJobRequest,
    current_user: Annotated[UserInDB, Depends(require_admin)],
    job_service: Annotated[JobService, Depends(get_job_service)]
):
    """建立新工作（需要管理員權限）"""
    try:
        job = job_service.create_job(job_data)
        return job
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[Job])
def get_all_jobs(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    job_service: Annotated[JobService, Depends(get_job_service)]
):
    """取得所有工作（需要認證）"""
    return job_service.get_all_jobs()


@router.get("/{job_id}", response_model=Job)
def get_job(
    job_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    job_service: Annotated[JobService, Depends(get_job_service)]
):
    """取得特定工作（需要認證）"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="工作不存在")
    return job


@router.get("/{job_id}/applications", response_model=List[Application])
def get_job_applications(
    job_id: str,
    current_user: Annotated[UserInDB, Depends(require_admin)],
    job_service: Annotated[JobService, Depends(get_job_service)],
    application_service: Annotated[ApplicationService, Depends(get_application_service)]
):
    """取得工作的報班清單（需要管理員權限）"""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="工作不存在")
    
    applications = application_service.get_job_applications(job_id)
    return applications


@router.get("/applications/all", response_model=List[Application])
def get_all_applications(
    current_user: Annotated[UserInDB, Depends(require_admin)],
    application_service: Annotated[ApplicationService, Depends(get_application_service)]
):
    """取得所有報班記錄（需要管理員權限）"""
    from app.core.database import SessionLocal
    from app.models.job import ApplicationModel
    from sqlalchemy.sql import func
    
    db = SessionLocal()
    try:
        app_models = db.query(ApplicationModel).order_by(ApplicationModel.applied_at.desc()).all()
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
        db.close()
