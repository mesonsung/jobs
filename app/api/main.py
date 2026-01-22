"""
FastAPI 主應用程式
"""
from fastapi import FastAPI
from app.core.database import init_db
from app.api.routes import auth, geocoding, jobs, users

# 建立 FastAPI 應用程式
api_app = FastAPI(title="Good Jobs 報班系統 API", version="1.0.0")

# 初始化資料庫
try:
    init_db()
    print("✅ 資料庫初始化完成")
except Exception as e:
    print(f"⚠️  資料庫初始化失敗：{e}")
    print("⚠️  將繼續使用記憶體儲存（資料不會持久化）")

# 註冊路由
api_app.include_router(auth.router)
api_app.include_router(geocoding.router)
api_app.include_router(jobs.router)
api_app.include_router(users.router)


@api_app.get("/")
def root():
    """根路徑"""
    return {
        "message": "Good Jobs 報班系統 API",
        "version": "1.0.0",
        "docs": "/docs"
    }
