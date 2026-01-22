"""
LINE 訊息發送服務
"""
from typing import List, Dict
import requests


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
            print(f"❌ LINE API 錯誤：{e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   回應內容：{e.response.text}")
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
