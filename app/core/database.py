"""
資料庫核心設定
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import DATABASE_URL

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
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 資料庫表已建立")
    except Exception as e:
        print(f"⚠️  資料庫初始化失敗：{e}")
        raise
