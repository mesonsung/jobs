"""
Good Jobs 報班系統 - 主入口點

注意：此檔案應該通過根目錄的 main.py 或使用 'python -m app.main' 執行
不要直接在 app/ 目錄內執行此檔案
"""
import os
import sys
import socket
import threading
from datetime import date, timedelta

from app.core.logger import setup_logger

# 設置 logger
logger = setup_logger(__name__)

# 檢查是否能夠正確導入 app 模組
# 在 Docker 容器中，工作目錄是 /app，這是正常的
if __name__ == "__main__":
    try:
        # 嘗試導入 app.config 來檢查模組路徑是否正確
        import app.config
    except ImportError:
        # 如果無法導入，可能是因為在錯誤的目錄執行
        # 檢查是否在 app/ 子目錄內（本地開發環境）
        current_dir = os.path.basename(os.getcwd())
        if current_dir == "app" and "/app" not in os.getcwd():
            # 在本地開發環境的 app/ 目錄內執行
            logger.error("錯誤：請從專案根目錄執行，不要進入 app/ 目錄")
            logger.info("正確的執行方式：")
            logger.info("  python3 main.py")
            logger.info("  或")
            logger.info("  python3 -m app.main")
            sys.exit(1)
        else:
            # 其他導入錯誤，重新拋出
            raise

try:
    import uvicorn
except ImportError:
    logger.error("錯誤：未安裝 uvicorn")
    logger.info("請執行：pip install uvicorn[standard]")
    logger.info("或：pip install -r requirements.txt")
    sys.exit(1)

from app.config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    GOOGLE_MAPS_API_KEY,
    LINE_BOT_PORT,
    FASTAPI_PORT
)
from app.core.database import init_db
from app.core.logger import get_uvicorn_log_config
from app.services.job_service import JobService
from app.services.application_service import ApplicationService
from app.services.geocoding_service import GeocodingService
from app.services.auth_service import AuthService
from app.bot.bot import PartTimeJobBot
from app.api.main import api_app
from app.models.schemas import CreateJobRequest


def create_sample_jobs(job_service: JobService, geocoding_service: GeocodingService):
    """建立測試工作資料"""
    from app.core.database import SessionLocal
    from app.models.job import JobModel
    
    # 檢查是否已有工作（從資料庫查詢）
    db = SessionLocal()
    try:
        existing_jobs = db.query(JobModel).count()
        if existing_jobs > 0:
            logger.info("已有工作資料，跳過建立測試資料")
            return
    finally:
        db.close()
    
    # 建立幾個測試工作
    sample_jobs = [
        {
            "name": "餐廳服務員",
            "location": "台北市信義區信義路五段7號",
            "date": (date.today() + timedelta(days=3)).strftime('%Y-%m-%d'),
            "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
            "location_image_url": None
        },
        {
            "name": "活動工作人員",
            "location": "桃園市桃園區中正五街196號",
            "date": (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "shifts": ["早班:09-18", "晚班:18-22"],
            "location_image_url": None
        },
        {
            "name": "展覽導覽員",
            "location": "新北市鶯歌區鳳吉一街193號",
            "date": (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            "shifts": ["早班:10-18"],
            "location_image_url": None
        }
    ]
    
    # 創建帶有地理編碼服務的 JobService
    job_service_with_geocoding = JobService(geocoding_service=geocoding_service)
    
    for job_data in sample_jobs:
        job_request = CreateJobRequest(**job_data)
        job = job_service_with_geocoding.create_job(job_request)
        logger.info(f"已建立測試工作：{job.name} (ID: {job.id})")
    
    logger.info(f"共建立 {len(sample_jobs)} 個測試工作")


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """檢查指定 port 是否已被使用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def main():
    """主函數"""
    # 初始化資料庫
    try:
        init_db()
        logger.info("資料庫初始化完成")
    except Exception as e:
        logger.warning(f"資料庫初始化失敗：{e}", exc_info=True)
        logger.warning("將繼續使用記憶體儲存（資料不會持久化）")
    
    # 初始化服務
    geocoding_service = GeocodingService(api_key=GOOGLE_MAPS_API_KEY)
    job_service = JobService(geocoding_service=geocoding_service)
    application_service = ApplicationService()
    auth_service = AuthService()
    
    # 建立測試資料
    create_sample_jobs(job_service, geocoding_service)
    
    # 建立 Bot 實例
    bot = PartTimeJobBot(
        channel_access_token=LINE_CHANNEL_ACCESS_TOKEN,
        job_service=job_service,
        application_service=application_service,
        channel_secret=LINE_CHANNEL_SECRET,
        auth_service=auth_service
    )
    
    # 檢查是否在主進程中（Flask reloader 會產生子進程）
    is_main_process = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'
    
    # 啟動 FastAPI（後台 API）- 只在主進程且 port 未被佔用時啟動
    def run_fastapi():
        try:
            # 使用統一的日誌配置
            log_config = get_uvicorn_log_config()
            uvicorn.run(
                api_app, 
                host="0.0.0.0", 
                port=FASTAPI_PORT,
                log_config=log_config
            )
        except Exception as e:
            logger.warning(f"FastAPI 啟動失敗：{e}", exc_info=True)
    
    # 啟動 LINE Bot（前台）
    # 在生產環境中，debug 應設為 False，並使用 Gunicorn
    # 可以通過環境變數控制：DEBUG=false, USE_GUNICORN=true
    debug_mode = os.getenv("DEBUG", "true").lower() == "true"
    use_gunicorn = os.getenv("USE_GUNICORN", "false").lower() == "true"
    
    def run_line_bot():
        bot.run(
            port=LINE_BOT_PORT, 
            debug=debug_mode, 
            use_threading=False,
            use_gunicorn=use_gunicorn
        )
    
    # 只在主進程且 port 未被佔用時啟動 FastAPI
    if is_main_process and not is_port_in_use(FASTAPI_PORT):
        fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
        fastapi_thread.start()
        logger.info(f"FastAPI 伺服器已啟動，監聽 http://0.0.0.0:{FASTAPI_PORT}")
        logger.info(f"API 文件：http://localhost:{FASTAPI_PORT}/docs")
    elif is_port_in_use(FASTAPI_PORT) and is_main_process:
        logger.info(f"FastAPI 伺服器已在運行（port {FASTAPI_PORT} 已被佔用）")
    
    # 在前景執行 LINE Bot
    logger.info("啟動 LINE Bot 伺服器...")
    run_line_bot()


if __name__ == "__main__":
    main()
