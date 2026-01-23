"""
Good Jobs 報班系統 - LINE Bot 主應用程式
"""
from typing import Dict, Optional
import json
import hmac
import hashlib
import base64
import urllib.parse
from flask import Flask, request

from app.services.job_service import JobService
from app.services.application_service import ApplicationService
from app.services.line_message_service import LineMessageService
from app.services.auth_service import AuthService
from app.bot.handler import JobHandler, registration_states, edit_profile_states
from app.core.logger import setup_logger, setup_gunicorn_logger, DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT

# 在模組導入時就配置好 Gunicorn logger，確保啟動訊息也使用統一格式
# 這樣當 Gunicorn 啟動時，所有日誌都會使用統一的格式
setup_gunicorn_logger()

# 設置 logger
logger = setup_logger(__name__)

# Gunicorn 需要這個變數來獲取 Flask 應用程式
# 這將在 PartTimeJobBot 初始化時設置
flask_app = None

def get_flask_app():
    """Gunicorn 使用的 WSGI 應用程式獲取函數（返回應用程式實例）"""
    global flask_app
    if flask_app is None:
        # 如果還沒有實例，創建一個臨時實例
        # 這通常不會發生，因為 main.py 會先創建實例
        from app.config import LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
        from app.services.job_service import JobService
        from app.services.application_service import ApplicationService
        from app.services.auth_service import AuthService
        from app.services.geocoding_service import GeocodingService
        
        geocoding_service = GeocodingService()
        job_service = JobService(geocoding_service=geocoding_service)
        application_service = ApplicationService()
        auth_service = AuthService()
        
        temp_bot = PartTimeJobBot(
            channel_access_token=LINE_CHANNEL_ACCESS_TOKEN,
            job_service=job_service,
            application_service=application_service,
            channel_secret=LINE_CHANNEL_SECRET,
            auth_service=auth_service
        )
        flask_app = temp_bot.flask_app
    return flask_app

class PartTimeJobBot:
    """Good Jobs 報班系統主應用程式"""
    
    def __init__(self, channel_access_token: str, job_service: JobService, application_service: ApplicationService, channel_secret: Optional[str] = None, auth_service: Optional[AuthService] = None):
        # 初始化服務
        self.job_service = job_service
        self.application_service = application_service
        self.message_service = LineMessageService(channel_access_token)
        self.handler = JobHandler(self.job_service, self.application_service, self.message_service, auth_service)
        self.channel_secret = channel_secret
        
        # 建立 Flask 應用程式（用於 LINE Webhook）
        self.flask_app = Flask(__name__)
        self._setup_routes()
        
        # 註冊報班帳號 Flask 應用程式實例供 Gunicorn 使用
        global flask_app
        flask_app = self.flask_app
    
    def _setup_routes(self):
        """設定路由"""
        @self.flask_app.route("/webhook", methods=['POST'])
        def webhook():  # noqa: F841
            """LINE Webhook 處理函數（由 Flask 框架自動調用）"""
            return self.handle_webhook()
    
    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """
        驗證 LINE Webhook 請求簽名
        
        參數:
            body: 請求原始 body（bytes）
            signature: X-Line-Signature header 的值
        
        返回:
            bool: 驗證是否通過
        """
        if not self.channel_secret:
            # 如果沒有設定 channel_secret，跳過驗證（開發模式）
            logger.warning("未設定 Channel Secret，跳過簽名驗證")
            return True
        
        try:
            # 使用 Channel Secret 和請求體計算 HMAC-SHA256
            hash_value = hmac.new(
                self.channel_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).digest()
            
            # 轉換為 base64
            expected_signature = base64.b64encode(hash_value).decode('utf-8')
            
            # 比較簽名（使用安全比較避免時間攻擊）
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"簽名驗證錯誤：{e}", exc_info=True)
            return False
    
    def handle_webhook(self):
        """處理 LINE Webhook"""
        try:
            # 驗證請求簽名
            signature = request.headers.get('X-Line-Signature', '')
            body = request.get_data()
            
            if not self._verify_signature(body, signature):
                logger.warning(f"Webhook 簽名驗證失敗，收到的簽名：{signature[:20]}...")
                return 'Forbidden', 403
            
            # 解析 JSON 資料
            data = request.get_json()
            
            # 記錄接收到的資料（DEBUG 級別）
            #logger.debug(f"收到 Webhook 資料：{json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 處理不同類型的事件
            for event in data.get('events', []):
                try:
                    event_type = event.get('type')
                    reply_token = event.get('replyToken')
                    user_id = event['source'].get('userId', 'unknown')
                    
                    if event_type == 'message':
                        self._handle_message(event, reply_token, user_id)
                    elif event_type == 'postback':
                        self._handle_postback(event, reply_token, user_id)
                except Exception as e:
                    logger.error(f"處理事件時發生錯誤：{e}", exc_info=True)
                    logger.debug(f"事件資料：{json.dumps(data, indent=2, ensure_ascii=False)}")
                    # 嘗試發送錯誤訊息給使用者
                    try:
                        if reply_token:
                            self.message_service.send_text(
                                reply_token,
                                "❌ 處理您的請求時發生錯誤，請稍後再試。"
                            )
                    except:
                        pass
            
            return 'OK', 200
        except Exception as e:
            logger.error(f"Webhook 處理錯誤：{e}", exc_info=True)
            return 'OK', 200  # 即使出錯也返回 OK，避免 LINE 重試
    
    def _handle_message(self, event: Dict, reply_token: str, user_id: str) -> None:
        """處理文字訊息"""
        message_text = event['message'].get('text', '')
        
        logger.debug(f"_handle_message: 收到文字訊息：{message_text} (user_id: {user_id})")
        # 檢查是否在註冊報班帳號流程中
        logger.debug(f"_handle_message: registration_states: {registration_states} (user_id: {user_id})")
        if user_id in registration_states:
            self.handler.handle_register_input(reply_token, user_id, message_text)
            return
        
        # 檢查是否在修改資料流程中
        if user_id in edit_profile_states:
            self.handler.handle_edit_profile_input(reply_token, user_id, message_text)
            return
        
        if message_text.strip().lower() in ['選單', 'menu', 'menus']:
            self.handler.show_main_menu(reply_token, user_id)
        elif message_text.strip().lower() in ['工作列表', '工作', 'jobs', 'list']:
            self.handler.show_available_jobs(reply_token, user_id)
        elif message_text.strip().lower() in ['已報班', '我的報班', '報班記錄', 'applications']:
            self.handler.show_user_applications(reply_token, user_id)
        elif message_text.strip().lower() in ['註冊報班帳號', 'register']:
            self.handler.handle_register(reply_token, user_id)
        else:
            # 預設顯示主選單
            self.handler.show_main_menu(reply_token, user_id)
    
    def _handle_postback(self, event: Dict, reply_token: str, user_id: str) -> None:
        """處理 postback 事件"""
        postback_data = event['postback'].get('data', '')
        logger.debug(f"_handle_postback: 收到 postback: {postback_data} (user_id: {user_id})")
        
        # 解析 postback data
        parsed_data = urllib.parse.parse_qs(postback_data)
        action = parsed_data.get('action', [''])[0]
        step = parsed_data.get('step', [''])[0]
        job_id = parsed_data.get('job_id', [''])[0]
        shift = parsed_data.get('shift', [''])[0]
        
        # 解碼 shift（如果有）
        if shift:
            shift = urllib.parse.unquote(shift)
        
        # 根據不同的步驟處理
        if action == 'register':
            if step == 'register':
                self.handler.handle_register(reply_token, user_id)
        elif action == 'edit_profile':
            if step == 'select_field':
                self.handler.handle_edit_profile(reply_token, user_id)
            elif step == 'input':
                field = parsed_data.get('field', [''])[0]
                if field:
                    # 設定修改狀態並提示輸入
                    edit_profile_states[user_id] = {'field': field}
                    user = self.handler.auth_service.get_user_by_line_id(user_id) if self.handler.auth_service else None
                    
                    if field == 'phone':
                        current = user.phone if user and user.phone else '未填寫'
                        prompt = f"📱 修改手機號碼\n\n目前的手機號碼：{current}\n\n請輸入新的手機號碼（格式：09XX-XXX-XXX 或 09XXXXXXXX）：\n\n或輸入「取消」取消修改。"
                    elif field == 'address':
                        current = user.address if user and user.address else '未填寫'
                        prompt = f"📍 修改地址\n\n目前的地址：{current}\n\n請輸入新的地址：\n\n或輸入「取消」取消修改。"
                    elif field == 'email':
                        current = user.email if user and user.email else '未填寫'
                        prompt = f"📧 修改 Email\n\n目前的 Email：{current}\n\n請輸入新的 Email：\n\n（可選，輸入「跳過」可清除 Email）\n或輸入「取消」取消修改。"
                    else:
                        prompt = "請輸入新值："
                    
                    self.handler.message_service.send_text(reply_token, prompt)
        elif action == 'view_profile':
            if step == 'view':
                self.handler.show_user_profile(reply_token, user_id)
        elif action == 'delete_registration':
            if step == 'confirm':
                self.handler.handle_delete_registration(reply_token, user_id)
            elif step == 'confirm_delete':
                self.handler.handle_confirm_delete_registration(reply_token, user_id)
        elif action == 'job':
            if step == 'list':
                self.handler.show_available_jobs(reply_token, user_id)
            elif step == 'detail':
                if job_id:
                    self.handler.show_job_detail(reply_token, user_id, job_id)
            elif step == 'apply':
                if job_id:
                    self.handler.handle_apply_job(reply_token, user_id, job_id)
            elif step == 'select_shift':
                if job_id and shift:
                    self.handler.handle_select_shift(reply_token, user_id, job_id, shift)
            elif step == 'cancel':
                if job_id:
                    self.handler.handle_cancel_application(reply_token, user_id, job_id)
            elif step == 'confirm_cancel':
                if job_id:
                    self.handler.handle_confirm_cancel(reply_token, user_id, job_id)
            elif step == 'my_applications':
                self.handler.show_user_applications(reply_token, user_id)
            elif step == 'menu':
                self.handler.show_main_menu(reply_token, user_id)
    
    def run(self, port: int = 3000, debug: bool = False, use_threading: bool = True, use_gunicorn: Optional[bool] = None):
        """
        啟動伺服器
        
        參數:
            port: 連接埠號
            debug: 是否啟用除錯模式
            use_threading: 是否使用執行緒在背景執行
            use_gunicorn: 是否使用 Gunicorn（None 時根據環境自動判斷）
        """
        import os
        
        # 自動判斷是否使用 Gunicorn
        if use_gunicorn is None:
            # 如果設置了 USE_GUNICORN 環境變數，使用它
            use_gunicorn = os.getenv("USE_GUNICORN", "false").lower() == "true"
            # 或者在非除錯模式下自動使用 Gunicorn
            if not debug and not use_gunicorn:
                use_gunicorn = True
        
        # 如果使用 Gunicorn
        if use_gunicorn:
            try:
                import gunicorn.app.wsgiapp as wsgi
                import sys
                
                # 確保 Flask 應用程式已註冊報班帳號
                global flask_app
                flask_app = self.flask_app
                
                # 配置 Gunicorn logger 使用統一的日誌格式
                setup_gunicorn_logger()
                
                # 設置 Gunicorn 參數
                workers = os.getenv("GUNICORN_WORKERS", "2")
                # Gunicorn 使用小寫的日誌級別，需要轉換
                app_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
                gunicorn_log_level_map = {
                    "DEBUG": "debug",
                    "INFO": "info",
                    "WARNING": "warning",
                    "ERROR": "error",
                    "CRITICAL": "critical"
                }
                log_level = gunicorn_log_level_map.get(app_log_level, "info")
                
                # 統一的 access log 格式
                # 從格式中移除 %(t)s（Gunicorn 的默認時間戳 [23/Jan/2026:03:08:36 +0000]）
                # 當不設置 --access-logfile 時，access log 會通過 gunicorn.access logger
                # 由 logging formatter 添加統一的時間戳格式：%Y-%m-%d %H:%M:%S
                # 格式：狀態碼 方法 路徑 查詢字符串 - 響應時間(微秒)
                # 實際輸出會是：2026-01-23 11:00:00 - gunicorn.access - INFO - 200 POST /webhook - 157237μs
                # 注意：響應時間 %(D)s 是微秒，要轉換為毫秒需要除以 1000，但格式不支持計算
                access_log_format = '%(s)s %(m)s %(U)s%(q)s - %(D)sμs'
                
                # Gunicorn 需要直接引用 Flask 應用程式實例
                # 使用模組級變數 flask_app
                # 使用配置檔案以確保 on_starting hook 被調用
                import os as os_module
                config_path = os_module.path.join(
                    os_module.path.dirname(os_module.path.dirname(os_module.path.dirname(__file__))),
                    "gunicorn_config.py"
                )
                sys.argv = [
                    "gunicorn",
                    "--config", config_path,
                    "--bind", f"0.0.0.0:{port}",
                    "--workers", str(workers),
                    "--worker-class", "sync",
                    "--timeout", "120",
                    "--error-logfile", "-",
                    "--access-logformat", access_log_format,
                    "--log-level", log_level,
                    "--preload",
                    "app.bot.bot:flask_app"
                ]
                
                # 注意：我們移除了 --access-logfile "-"
                # 這樣 access log 會通過 Python logging 系統（gunicorn.access logger）
                # setup_gunicorn_logger() 已經配置了 gunicorn.access logger 使用統一的格式
                # 如果不設置 --access-logfile，Gunicorn 會使用默認的 logging 系統輸出 access log
                
                logger.info(f"使用 Gunicorn 啟動 LINE Bot 伺服器")
                logger.info(f"監聽地址：0.0.0.0:{port}")
                logger.info(f"Workers：{workers}")
                logger.info(f"日誌級別：{log_level}")
                wsgi.run()
            except ImportError:
                logger.warning("Gunicorn 未安裝，回退到 Flask 開發伺服器")
                logger.info("安裝方式：pip install gunicorn")
                use_gunicorn = False
            except Exception as e:
                logger.warning(f"Gunicorn 啟動失敗：{e}，回退到 Flask 開發伺服器", exc_info=True)
                use_gunicorn = False
        
        # 如果不使用 Gunicorn（開發模式）
        if not use_gunicorn:
            import warnings
            import logging
            
            # 抑制 Flask 開發伺服器警告（在開發環境中）
            warnings.filterwarnings("ignore", message=".*development server.*")
            logging.getLogger("werkzeug").setLevel(logging.ERROR)
            
            if use_threading:
                import threading
                def run_server():
                    self.flask_app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False, use_debugger=False)
                
                thread = threading.Thread(target=run_server, daemon=True)
                thread.start()
                logger.info(f"LINE Bot 伺服器已在背景啟動，監聽 0.0.0.0:{port}")
                logger.warning("注意：在 Jupyter 中，伺服器會在背景執行，要停止伺服器請重新啟動 kernel")
            else:
                self.flask_app.run(host='0.0.0.0', port=port, debug=debug)
                logger.info(f"LINE Bot 伺服器已啟動，監聽 0.0.0.0:{port}")

