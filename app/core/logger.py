"""
應用程式日誌配置
"""
import logging
import sys
import os
import re
from typing import Optional, Dict, Any
from datetime import datetime

# 統一日誌格式（用於所有組件：logger, Gunicorn, Uvicorn）
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class UnifiedLogFormatter:
    """
    統一的日誌格式化器，用於攔截和重新格式化 Gunicorn 的啟動訊息
    """
    def __init__(self, original_stream):
        self.original_stream = original_stream
        # Gunicorn 啟動訊息的格式：[timestamp] [pid] [level] message
        # 例如：[2026-01-23 04:04:46 +0000] [1] [INFO] Starting gunicorn 24.0.0
        self.gunicorn_pattern = re.compile(
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4})\] \[(\d+)\] \[(\w+)\] (.+)'
        )
        self._is_formatting = False  # 防止無限遞迴
    
    def write(self, message):
        """攔截寫入的訊息並重新格式化"""
        if not message or not message.strip():
            self.original_stream.write(message)
            return
        
        # 防止無限遞迴：如果正在格式化，直接輸出
        if self._is_formatting:
            self.original_stream.write(message)
            return
        
        # 嘗試匹配 Gunicorn 的啟動訊息格式
        stripped_message = message.strip()
        match = self.gunicorn_pattern.match(stripped_message)
        if match:
            # 解析 Gunicorn 格式的時間戳
            gunicorn_timestamp = match.group(1)
            pid = match.group(2)
            level = match.group(3)
            msg = match.group(4)
            
            try:
                # 將 Gunicorn 的時間戳轉換為統一格式
                # Gunicorn 格式：2026-01-23 04:04:46 +0000
                dt = datetime.strptime(gunicorn_timestamp, "%Y-%m-%d %H:%M:%S %z")
                # 轉換為統一格式：2026-01-23 04:04:46
                unified_timestamp = dt.strftime(DEFAULT_DATE_FORMAT)
                
                # 重新格式化為統一格式
                formatted_message = f"{unified_timestamp} - gunicorn - {level} - {msg}\n"
                self._is_formatting = True
                try:
                    self.original_stream.write(formatted_message)
                finally:
                    self._is_formatting = False
                return
            except (ValueError, AttributeError):
                # 如果解析失敗，使用原始訊息
                pass
        
        # 如果不是 Gunicorn 格式，直接輸出
        self.original_stream.write(message)
    
    def flush(self):
        self.original_stream.flush()
    
    def __getattr__(self, name):
        return getattr(self.original_stream, name)

# Gunicorn access log 格式（統一格式）
GUNICORN_ACCESS_LOG_FORMAT = '%(t)s - %(s)s - %(m)s %(U)s%(q)s - %(D)sms'

# Gunicorn error log 格式（統一格式）
GUNICORN_ERROR_LOG_FORMAT = "%(asctime)s - gunicorn - %(levelname)s - %(message)s"

# 日誌級別映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logger(
    name: str = "good_job",
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None
) -> logging.Logger:
    """
    設置並返回 logger 實例
    
    參數:
        name: logger 名稱（通常是模組名稱）
        level: 日誌級別（從環境變數 LOG_LEVEL 讀取，預設為 INFO）
        format_string: 日誌格式字串
        date_format: 日期格式字串
    
    返回:
        logging.Logger: 配置好的 logger 實例
    """
    # 從環境變數讀取日誌級別
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # 轉換為 logging 級別
    log_level = LOG_LEVELS.get(level, logging.INFO)
    
    # 確保 root logger 有基本配置（避免日誌丟失）
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # 在 Docker/Gunicorn 環境中，使用 stderr 確保日誌能被 docker logs 捕獲
        # Gunicorn 的 error-logfile 會捕獲 stderr
        root_handler = logging.StreamHandler(sys.stderr)
        root_handler.setLevel(logging.WARNING)  # root logger 只顯示 WARNING 及以上
        root_formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
        root_handler.setFormatter(root_formatter)
        root_logger.addHandler(root_handler)
        root_logger.setLevel(logging.WARNING)
    
    # 創建 logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 設置 propagate=False 確保日誌只在當前 logger 處理，不會向上傳播
    logger.propagate = False
    
    # 清除現有的 handlers（如果有），重新配置以確保正確的格式和級別
    logger.handlers.clear()
    
    # 在 Docker/Gunicorn 環境中，使用 stderr 確保日誌能被 docker logs 捕獲
    # 這樣可以確保日誌在 docker logs -f 中正常顯示
    # Gunicorn 的 --error-logfile - 會捕獲 stderr
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    
    # 設置格式
    if format_string is None:
        format_string = DEFAULT_LOG_FORMAT
    if date_format is None:
        date_format = DEFAULT_DATE_FORMAT
    
    formatter = logging.Formatter(format_string, date_format)
    console_handler.setFormatter(formatter)
    
    # 添加 handler
    logger.addHandler(console_handler)
    
    return logger


# 創建預設 logger（用於直接導入）
default_logger = setup_logger("good_job")


def setup_gunicorn_logger():
    """
    配置 Gunicorn 的 logger 使用統一的日誌格式
    這需要在 Gunicorn 啟動前調用
    
    此函數會攔截 Gunicorn 的啟動訊息並重新格式化為統一格式。
    """
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_level_value = LOG_LEVELS.get(log_level, logging.INFO)
    
    # 攔截 stderr 以重新格式化 Gunicorn 的啟動訊息
    # 只有在 stderr 還沒有被攔截時才進行攔截
    if not isinstance(sys.stderr, UnifiedLogFormatter):
        sys.stderr = UnifiedLogFormatter(sys.stderr)
    
    # 首先配置 root logger，確保所有日誌都使用統一格式
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_handler = logging.StreamHandler(sys.stderr)
        root_handler.setLevel(log_level_value)
        root_formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
        root_handler.setFormatter(root_formatter)
        root_logger.addHandler(root_handler)
        root_logger.setLevel(log_level_value)
    else:
        # 如果 root logger 已有 handlers，確保它們使用統一格式
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT))
    
    # 配置 gunicorn.error logger
    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    gunicorn_error_logger.setLevel(log_level_value)
    gunicorn_error_logger.propagate = False
    
    # 清除現有 handlers
    gunicorn_error_logger.handlers.clear()
    
    # 添加統一的 handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level_value)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
    handler.setFormatter(formatter)
    gunicorn_error_logger.addHandler(handler)
    
    # 配置 gunicorn.access logger 使用統一的格式
    # 這樣 access log 會通過 Python logging 系統，使用統一的格式
    gunicorn_access_logger = logging.getLogger("gunicorn.access")
    gunicorn_access_logger.setLevel(log_level_value)
    gunicorn_access_logger.propagate = False
    
    # 清除現有 handlers
    gunicorn_access_logger.handlers.clear()
    
    # 添加統一的 handler
    access_handler = logging.StreamHandler(sys.stderr)
    access_handler.setLevel(log_level_value)
    # Access log 格式：統一格式，訊息部分包含 HTTP 請求資訊
    access_formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
    access_handler.setFormatter(access_formatter)
    gunicorn_access_logger.addHandler(access_handler)


def get_uvicorn_log_config() -> Dict[str, Any]:
    """
    獲取 Uvicorn 的日誌配置（統一格式）
    
    返回:
        Dict: Uvicorn log_config 字典
    """
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    
    # 將應用程式的日誌級別映射到 Uvicorn 的日誌級別
    uvicorn_log_level_map = {
        "DEBUG": "debug",
        "INFO": "info",
        "WARNING": "warning",
        "ERROR": "error",
        "CRITICAL": "critical"
    }
    uvicorn_level = uvicorn_log_level_map.get(log_level, "info")
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": DEFAULT_LOG_FORMAT,
                "datefmt": DEFAULT_DATE_FORMAT,
            },
            "access": {
                "format": DEFAULT_LOG_FORMAT,
                "datefmt": DEFAULT_DATE_FORMAT,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": uvicorn_level.upper(),
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": uvicorn_level.upper(),
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": uvicorn_level.upper(),
                "propagate": False,
            },
        },
    }
