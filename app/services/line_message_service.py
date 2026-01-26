"""
LINE 訊息發送服務
"""
from typing import List, Dict
import requests

from app.core.logger import setup_logger

# 設置 logger
logger = setup_logger(__name__)


class LineMessageService:
    """LINE 訊息發送服務"""
    
    def __init__(self, channel_access_token: str):
        self.token = channel_access_token
        self.api_url = "https://api.line.me/v2/bot/message/reply"
    
    def _get_headers(self) -> Dict[str, str]:
        """取得 API 請求標頭"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def send_text(self, reply_token: str, text: str) -> requests.Response:
        """發送文字訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": [{
                "type": "text",
                "text": text
            }]
        }
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )
    
    def send_flex_message(self, reply_token: str, alt_text: str, contents: Dict) -> requests.Response:
        """發送 Flex 訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": [{
                "type": "flex",
                "altText": alt_text,
                "contents": contents
            }]
        }
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )
    
    def send_multiple_messages(self, reply_token: str, messages: List[Dict]) -> requests.Response:
        """在同一個回覆中發送多個訊息"""
        payload = {
            "replyToken": reply_token,
            "messages": messages
        }
        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()  # 如果狀態碼不是 2xx，會拋出異常
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"LINE API 錯誤：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            raise
    
    def send_buttons_template(self, reply_token: str, title: str, text: str, actions: List[Dict]) -> requests.Response:
        """發送按鈕範本訊息"""
        # LINE API 限制：template/text 不能超過 60 字元
        if len(text) > 60:
            text = text[:57] + "..."
        
        buttons_template = {
            "type": "template",
            "altText": title,
            "template": {
                "type": "buttons",
                "title": title,
                "text": text,
                "actions": actions
            }
        }
        
        payload = {
            "replyToken": reply_token,
            "messages": [buttons_template]
        }
        
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload,
            timeout=10
        )
    
    def send_carousel_template(self, reply_token: str, alt_text: str, columns: List[Dict]) -> requests.Response:
        """
        發送輪播範本訊息（Carousel Template）
        
        參數:
            reply_token: LINE 回覆令牌
            alt_text: 替代文字（當用戶的裝置不支援模板訊息時顯示）
            columns: 輪播欄位列表（最多 10 個），每個欄位是一個 bubble 物件
                    格式：{
                        "thumbnailImageUrl": "圖片 URL（可選）",
                        "title": "標題（最多 40 字元）",
                        "text": "文字內容（最多 120 字元，建議 60 字元以內）",
                        "actions": [按鈕列表，最多 3 個]
                    }
        """
        # LINE API 限制：Carousel 最多 10 個 columns
        if len(columns) > 10:
            logger.warning(f"Carousel columns 超過 10 個，將只發送前 10 個")
            columns = columns[:10]
        
        carousel_template = {
            "type": "template",
            "altText": alt_text,
            "template": {
                "type": "carousel",
                "columns": columns
            }
        }
        
        payload = {
            "replyToken": reply_token,
            "messages": [carousel_template]
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"發送 Carousel Template 失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            raise
