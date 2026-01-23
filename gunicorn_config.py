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


def on_starting(server):
    """
    Gunicorn 啟動時的 hook
    確保日誌系統已配置為統一格式
    """
    # 在 Gunicorn 啟動時配置日誌系統
    # 注意：Gunicorn 的啟動訊息（如 "Starting gunicorn 24.0.0"）是在此 hook 
    # 之前就輸出的，所以無法直接控制它們的格式
    from app.core.logger import setup_gunicorn_logger
    setup_gunicorn_logger()
