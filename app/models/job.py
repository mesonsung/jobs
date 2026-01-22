"""
工作相關資料模型
"""
from sqlalchemy import Column, String, Integer, Float, ARRAY, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class JobModel(Base):
    """工作資料表模型"""
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    shifts = Column(ARRAY(String), nullable=False)
    location_image_url = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 關聯
    applications = relationship("ApplicationModel", back_populates="job", cascade="all, delete-orphan")


class ApplicationModel(Base):
    """報班記錄資料表模型"""
    __tablename__ = "applications"
    
    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    user_name = Column(String, nullable=True)
    shift = Column(String, nullable=False)
    applied_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    
    # 關聯
    job = relationship("JobModel", back_populates="applications")
