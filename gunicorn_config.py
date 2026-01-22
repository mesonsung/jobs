"""
Gunicorn 配置文件
"""
import multiprocessing
import os

# 綁定地址和端口
bind = f"0.0.0.0:{os.getenv('LINE_BOT_PORT', '3000')}"

# Worker 數量（建議：CPU 核心數 * 2 + 1）
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Worker 類型
worker_class = "sync"

# 超時設定（秒）
timeout = 120

# Keep-alive 連接時間（秒）
keepalive = 5

# 日誌設定
accesslog = "-"  # 輸出到 stdout
errorlog = "-"   # 輸出到 stderr
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# 進程名稱
proc_name = "good-job-bot"

# 最大請求數（達到後重啟 worker，防止記憶體洩漏）
max_requests = 1000
max_requests_jitter = 50

# 預載入應用程式（提高性能）
preload_app = True

# 優雅重啟超時時間
graceful_timeout = 30
