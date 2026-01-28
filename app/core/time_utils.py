"""
時間相關工具（台灣時區 UTC+8、寫入 DB 用 UTC）
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# 台灣時區 UTC+8
TAIWAN_TZ = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    """回傳目前 UTC 時間（naive datetime，供寫入 DB 使用）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_datetime_taiwan(dt: Optional[datetime]) -> Optional[str]:
    """
    將 datetime 轉為台灣時間字串（UTC+8），格式為 YYYY-MM-DD HH:MM:SS。
    若 dt 為 naive（無時區），視為 UTC 再換算為台灣時間。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TAIWAN_TZ).strftime('%Y-%m-%d %H:%M:%S')
