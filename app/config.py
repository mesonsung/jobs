"""
應用程式配置設定
"""
import os
from typing import Optional

# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv(
    "LINE_CHANNEL_ACCESS_TOKEN",
    "oZPbAQXckPCTbRPN67GNPlyG/MqToO3haMOIvWOI35PGg8ZdBYEVtOc1KdJ+zYLJjOJ8+/YGaEk4f7m6W1RavpsYIp+5k1taVZ47HYboydFvMbTQ4rxXlNGysl2q0sM79gbzVuGnzHkPL2mf9SfU1gdB04t89/1O/w1cDnyilFU="
)
LINE_CHANNEL_SECRET = os.getenv(
    "LINE_CHANNEL_SECRET",
    "793a80c83472d9ddf0451cad2dd4077c"
)

# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv(
    "GOOGLE_MAPS_API_KEY",
    "AIzaSyDqcXhRP7pJmQIlO_F86Oh8lSmEtOUgXaw"
)

# JWT 設定
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "your-secret-key-change-this-in-production"
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 天

# 資料庫設定
POSTGRES_USER = os.getenv("POSTGRES_USER", "goodjob")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "goodjob123")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "goodjob_db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# 管理員帳號設定
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# 伺服器設定
LINE_BOT_PORT = int(os.getenv("LINE_BOT_PORT", "3000"))
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "8880"))

# Rich Menu 設定（可選，如果未設定則不會自動設定 Rich Menu）
REGISTERED_USER_RICH_MENU_ID = os.getenv("REGISTERED_USER_RICH_MENU_ID", None)
UNREGISTERED_USER_RICH_MENU_ID = os.getenv("UNREGISTERED_USER_RICH_MENU_ID", None)
