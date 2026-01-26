"""
資料庫核心設定
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import DATABASE_URL
from app.core.logger import setup_logger

# 設置 logger
logger = setup_logger(__name__)

# 建立 Base 類別
Base = declarative_base()

# 建立資料庫引擎
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# 建立會話工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """取得資料庫會話（用於 FastAPI 依賴注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化資料庫，建立所有資料表"""
    # 導入所有模型，確保它們被註冊到 Base.metadata
    from app.models import (  # noqa: F401
        JobModel,
        ApplicationModel,
        UserModel,
        RegistrationStateModel,
    )
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("資料庫表已建立")
    except Exception as e:
        logger.warning(f"資料庫初始化失敗：{e}", exc_info=True)
        raise
