"""
FastAPI 主應用程式
"""
from fastapi import FastAPI
from app.core.database import init_db
from app.core.logger import setup_logger
from app.api.routes import auth, geocoding, jobs, users, rich_menu

# 設置 logger
logger = setup_logger(__name__)

# 建立 FastAPI 應用程式
api_app = FastAPI(title="Good Jobs 報班系統 API", version="1.0.0")

# 初始化資料庫
try:
    init_db()
    logger.info("資料庫初始化完成")
except Exception as e:
    logger.warning(f"資料庫初始化失敗：{e}", exc_info=True)
    logger.warning("將繼續使用記憶體儲存（資料不會持久化）")

# 註冊路由
api_app.include_router(auth.router)
api_app.include_router(geocoding.router)
api_app.include_router(jobs.router)
api_app.include_router(users.router)
api_app.include_router(rich_menu.router)


@api_app.get("/")
def root():
    """根路徑"""
    return {
        "message": "Good Jobs 報班系統 API",
        "version": "1.0.0",
        "docs": "/docs"
    }
