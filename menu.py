"""
模組化訂位系統

將訂位系統重構為模組化架構，包含：
1. ReservationService - 訂位業務邏輯
2. LineMessageService - LINE 訊息發送服務
3. ReservationHandler - 訂位事件處理器
4. ReservationBot - 主應用程式
"""

import requests
from flask import Flask, request
import json
import datetime
import urllib.parse
from typing import List, Dict, Tuple, Optional

# ==================== 模組 1: 訂位服務 (ReservationService) ====================

class ReservationService:
    """訂位業務邏輯服務"""
    
    def __init__(self):
        # 訂位記錄儲存（實際應用中應該使用資料庫）
        # 格式：{user_id: [訂位記錄1, 訂位記錄2, ...]}
        self.reservations: Dict[str, List[Dict]] = {}
    
    def create_reservation(self, user_id: str, date: str, time: str) -> Dict:
        """
        建立訂位記錄
        
        參數:
            user_id: 使用者ID
            date: 訂位日期
            time: 訂位時間
        
        返回:
            dict: 訂位記錄
        """
        if user_id not in self.reservations:
            self.reservations[user_id] = []
        
        # 產生訂位編號
        reservation_id = f"R{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        reservation = {
            "id": reservation_id,
            "date": date,
            "time": time,
            "created_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.reservations[user_id].append(reservation)
        return reservation
    
    def get_user_reservations(self, user_id: str) -> List[Dict]:
        """
        查詢使用者的所有訂位記錄
        
        參數:
            user_id: 使用者ID
        
        返回:
            list: 訂位記錄列表
        """
        return self.reservations.get(user_id, [])
    
    def cancel_reservation(self, user_id: str, reservation_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        取消訂位
        
        參數:
            user_id: 使用者ID
            reservation_id: 訂位編號
        
        返回:
            tuple: (是否成功, 取消的訂位記錄或錯誤訊息)
        """
        if user_id not in self.reservations:
            return False, None
        
        # 尋找並移除指定的訂位記錄
        for i, res in enumerate(self.reservations[user_id]):
            if res['id'] == reservation_id:
                canceled_reservation = self.reservations[user_id].pop(i)
                return True, canceled_reservation
        
        return False, None
    
    def get_reservation_by_id(self, user_id: str, reservation_id: str) -> Optional[Dict]:
        """
        根據訂位編號取得訂位記錄
        
        參數:
            user_id: 使用者ID
            reservation_id: 訂位編號
        
        返回:
            dict: 訂位記錄，如果找不到則返回 None
        """
        user_reservations = self.get_user_reservations(user_id)
        for res in user_reservations:
            if res['id'] == reservation_id:
                return res
        return None

# ==================== 模組 2: LINE 訊息服務 (LineMessageService) ====================

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
        """
        發送文字訊息
        
        參數:
            reply_token: 回覆 Token
            text: 訊息文字
        
        返回:
            requests.Response: API 回應
        """
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
            json=payload
        )
    
    def send_buttons_template(self, reply_token: str, title: str, text: str, actions: List[Dict]) -> requests.Response:
        """
        發送按鈕範本訊息
        
        參數:
            reply_token: 回覆 Token
            title: 標題
            text: 內容文字
            actions: 按鈕動作列表
        
        返回:
            requests.Response: API 回應
        """
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
            json=payload
        )
    
    def send_multiple_messages(self, reply_token: str, messages: List[Dict]) -> requests.Response:
        """
        在同一個回覆中發送多個訊息
        
        參數:
            reply_token: 回覆 Token
            messages: 訊息列表
        
        返回:
            requests.Response: API 回應
        """
        payload = {
            "replyToken": reply_token,
            "messages": messages
        }
        
        return requests.post(
            self.api_url,
            headers=self._get_headers(),
            json=payload
        )

# ==================== 模組 3: 訂位處理器 (ReservationHandler) ====================

class ReservationHandler:
    """訂位事件處理器"""
    
    def __init__(self, reservation_service: ReservationService, message_service: LineMessageService):
        self.reservation_service = reservation_service
        self.message_service = message_service
        
        # 日期對應表
        self.date_map = {
            'today': '今天',
            'tomorrow': '明天',
            'day_after_tomorrow': '後天'
        }
    
    def handle_start_reservation(self, reply_token: str) -> None:
        """處理開始訂位流程"""
        date_actions = [
            {
                "type": "postback",
                "label": "今天",
                "data": "action=reservation&step=date&date=today"
            },
            {
                "type": "postback",
                "label": "明天",
                "data": "action=reservation&step=date&date=tomorrow"
            },
            {
                "type": "postback",
                "label": "後天",
                "data": "action=reservation&step=date&date=day_after_tomorrow"
            }
        ]
        
        messages = [
            {
                "type": "text",
                "text": "請選擇訂位日期："
            },
            {
                "type": "template",
                "altText": "選擇日期",
                "template": {
                    "type": "buttons",
                    "title": "選擇日期",
                    "text": "請選擇您要訂位的日期：",
                    "actions": date_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_select_date(self, reply_token: str, postback_data: str) -> None:
        """處理選擇日期"""
        parsed_data = urllib.parse.parse_qs(postback_data)
        date_value = parsed_data.get('date', ['unknown'])[0]
        date_text = self.date_map.get(date_value, date_value)
        
        time_actions = [
            {
                "type": "postback",
                "label": "12:00",
                "data": f"action=reservation&step=time&date={date_value}&time=12:00"
            },
            {
                "type": "postback",
                "label": "18:00",
                "data": f"action=reservation&step=time&date={date_value}&time=18:00"
            },
            {
                "type": "postback",
                "label": "20:00",
                "data": f"action=reservation&step=time&date={date_value}&time=20:00"
            }
        ]
        
        messages = [
            {
                "type": "text",
                "text": f"您選擇了 {date_text}，請選擇用餐時間："
            },
            {
                "type": "template",
                "altText": "選擇時間",
                "template": {
                    "type": "buttons",
                    "title": "選擇時間",
                    "text": f"您選擇了 {date_text}，請選擇用餐時間：",
                    "actions": time_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_select_time(self, reply_token: str, user_id: str, postback_data: str) -> None:
        """處理選擇時間並完成訂位"""
        parsed_data = urllib.parse.parse_qs(postback_data)
        date_value = parsed_data.get('date', ['unknown'])[0]
        time_value = parsed_data.get('time', ['unknown'])[0]
        date_text = self.date_map.get(date_value, date_value)
        
        # 儲存訂位記錄
        reservation = self.reservation_service.create_reservation(user_id, date_text, time_value)
        
        # 發送訂位成功訊息
        success_message = f"""✅ 訂位成功！

📋 訂位資訊：
• 訂位編號：{reservation['id']}
• 日期：{date_text}
• 時間：{time_value}
• 建立時間：{reservation['created_at']}

感謝您的訂位，我們期待為您服務！"""
        
        self.message_service.send_text(reply_token, success_message)
    
    def handle_query_reservations(self, reply_token: str, user_id: str) -> None:
        """處理查詢訂位記錄"""
        user_reservations = self.reservation_service.get_user_reservations(user_id)
        
        if user_reservations:
            reservation_text = "📋 您的訂位記錄：\n\n"
            for i, res in enumerate(user_reservations, 1):
                reservation_text += f"{i}. 訂位編號：{res['id']}\n"
                reservation_text += f"   日期：{res['date']}\n"
                reservation_text += f"   時間：{res['time']}\n"
                reservation_text += f"   建立時間：{res['created_at']}\n\n"
            
            self.message_service.send_text(reply_token, reservation_text)
        else:
            self.message_service.send_text(
                reply_token,
                "❌ 您目前沒有任何訂位記錄。\n\n請使用「開始訂位」功能來建立新的訂位。"
            )
    
    def handle_cancel_reservation(self, reply_token: str, user_id: str) -> None:
        """處理取消訂位流程"""
        user_reservations = self.reservation_service.get_user_reservations(user_id)
        
        if not user_reservations:
            self.message_service.send_text(reply_token, "❌ 您目前沒有任何訂位記錄，無法取消。")
            return
        
        if len(user_reservations) == 1:
            # 只有一筆訂位，直接顯示確認按鈕
            self._show_cancel_confirmation(reply_token, user_reservations[0])
        else:
            # 有多筆訂位，顯示選擇按鈕
            self._show_reservation_selection(reply_token, user_reservations)
    
    def _show_cancel_confirmation(self, reply_token: str, reservation: Dict) -> None:
        """顯示取消確認畫面"""
        cancel_actions = [
            {
                "type": "postback",
                "label": "確認取消",
                "data": f"action=reservation&step=confirm_cancel&reservation_id={reservation['id']}"
            },
            {
                "type": "postback",
                "label": "不取消",
                "data": "action=reservation&step=menu"
            }
        ]
        
        cancel_text = f"""請確認要取消的訂位：

📋 訂位資訊：
• 訂位編號：{reservation['id']}
• 日期：{reservation['date']}
• 時間：{reservation['time']}
• 建立時間：{reservation['created_at']}"""
        
        messages = [
            {
                "type": "text",
                "text": cancel_text
            },
            {
                "type": "template",
                "altText": "確認取消訂位",
                "template": {
                    "type": "buttons",
                    "title": "確認取消訂位",
                    "text": "確定要取消這個訂位嗎？",
                    "actions": cancel_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def _show_reservation_selection(self, reply_token: str, reservations: List[Dict]) -> None:
        """顯示訂位選擇畫面"""
        cancel_actions = []
        for res in reservations[:4]:  # LINE 按鈕最多 4 個
            cancel_actions.append({
                "type": "postback",
                "label": f"{res['date']} {res['time']}",
                "data": f"action=reservation&step=select_cancel&reservation_id={res['id']}",
                "displayText": f"取消訂位：{res['id']}"
            })
        
        messages = [
            {
                "type": "text",
                "text": "請選擇要取消的訂位："
            },
            {
                "type": "template",
                "altText": "選擇要取消的訂位",
                "template": {
                    "type": "buttons",
                    "title": "選擇要取消的訂位",
                    "text": "您有多筆訂位記錄，請選擇要取消的訂位：",
                    "actions": cancel_actions
                }
            }
        ]
        
        self.message_service.send_multiple_messages(reply_token, messages)
    
    def handle_select_cancel(self, reply_token: str, user_id: str, reservation_id: str) -> None:
        """處理選擇要取消的訂位"""
        reservation = self.reservation_service.get_reservation_by_id(user_id, reservation_id)
        
        if reservation:
            self._show_cancel_confirmation(reply_token, reservation)
        else:
            self.message_service.send_text(reply_token, "❌ 找不到指定的訂位記錄。")
    
    def handle_confirm_cancel(self, reply_token: str, user_id: str, reservation_id: str) -> None:
        """處理確認取消訂位"""
        success, canceled_res = self.reservation_service.cancel_reservation(user_id, reservation_id)
        
        if success and canceled_res:
            cancel_message = f"""✅ 訂位已成功取消！

📋 已取消的訂位資訊：
• 訂位編號：{canceled_res['id']}
• 日期：{canceled_res['date']}
• 時間：{canceled_res['time']}

如有任何問題，歡迎隨時聯絡我們。"""
            self.message_service.send_text(reply_token, cancel_message)
        else:
            self.message_service.send_text(reply_token, "❌ 取消訂位失敗，請稍後再試。")
    
    def show_main_menu(self, reply_token: str) -> None:
        """顯示主選單"""
        actions = [
            {
                "type": "postback",
                "label": "開始訂位",
                "data": "action=reservation&step=start",
                "displayText": "我要開始訂位"
            },
            {
                "type": "postback",
                "label": "查詢訂位",
                "data": "action=reservation&step=query"
            },
            {
                "type": "postback",
                "label": "取消訂位",
                "data": "action=reservation&step=cancel"
            },
            {
                "type": "message",
                "label": "聯絡客服",
                "text": "我需要客服協助"
            }
        ]
        
        self.message_service.send_buttons_template(
            reply_token,
            "餐廳訂位系統",
            "請選擇您需要的服務：",
            actions
        )

# ==================== 模組 4: 主應用程式 (ReservationBot) ====================

class ReservationBot:
    """訂位系統主應用程式"""
    
    def __init__(self, channel_access_token: str):
        # 初始化服務
        self.reservation_service = ReservationService()
        self.message_service = LineMessageService(channel_access_token)
        self.handler = ReservationHandler(self.reservation_service, self.message_service)
        
        # 建立 Flask 應用程式
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """設定路由"""
        @self.app.route("/", methods=['POST'])
        def webhook():
            return self.handle_webhook()
    
    def handle_webhook(self):
        """處理 LINE Webhook"""
        data = request.get_json()
        
        # 印出接收到的資料（方便除錯）
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # 處理不同類型的事件
        for event in data.get('events', []):
            event_type = event.get('type')
            reply_token = event.get('replyToken')
            user_id = event['source'].get('userId', 'unknown')
            
            if event_type == 'message':
                self._handle_message(event, reply_token)
            elif event_type == 'postback':
                self._handle_postback(event, reply_token, user_id)
        
        return 'OK', 200
    
    def _handle_message(self, event: Dict, reply_token: str) -> None:
        """處理文字訊息"""
        message_text = event['message'].get('text', '')
        
        if message_text in ['選單', 'menu', 'Menu', 'MENU']:
            self.handler.show_main_menu(reply_token)
    
    def _handle_postback(self, event: Dict, reply_token: str, user_id: str) -> None:
        """處理 postback 事件"""
        postback_data = event['postback'].get('data', '')
        print(f"收到 postback: {postback_data}")
        
        # 解析 postback data
        parsed_data = urllib.parse.parse_qs(postback_data)
        action = parsed_data.get('action', [''])[0]
        step = parsed_data.get('step', [''])[0]
        
        # 根據不同的步驟處理
        if action == 'reservation':
            if step == 'start':
                self.handler.handle_start_reservation(reply_token)
            elif step == 'date':
                self.handler.handle_select_date(reply_token, postback_data)
            elif step == 'time':
                self.handler.handle_select_time(reply_token, user_id, postback_data)
            elif step == 'query':
                self.handler.handle_query_reservations(reply_token, user_id)
            elif step == 'cancel':
                self.handler.handle_cancel_reservation(reply_token, user_id)
            elif step == 'select_cancel':
                reservation_id = parsed_data.get('reservation_id', [''])[0]
                self.handler.handle_select_cancel(reply_token, user_id, reservation_id)
            elif step == 'confirm_cancel':
                reservation_id = parsed_data.get('reservation_id', [''])[0]
                self.handler.handle_confirm_cancel(reply_token, user_id, reservation_id)
            elif step == 'menu':
                self.handler.show_main_menu(reply_token)
    
    def run(self, port: int = 3000, debug: bool = False, use_threading: bool = True):
        """
        啟動伺服器
        
        參數:
            port: 連接埠號
            debug: 是否啟用除錯模式
            use_threading: 是否使用執行緒在背景執行（Jupyter 環境建議設為 True）
        """
        if use_threading:
            # 在 Jupyter 中使用執行緒在背景執行，避免 SystemExit
            import threading
            def run_server():
                self.app.run(port=port, debug=debug, use_reloader=False, use_debugger=False)
            
            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            print(f"✅ 伺服器已在背景啟動，監聽 port {port}")
            print("⚠️  注意：在 Jupyter 中，伺服器會在背景執行")
            print("   要停止伺服器，請重新啟動 kernel")
        else:
            # 一般模式（非 Jupyter 環境）
            self.app.run(port=port, debug=debug)

# ==================== 使用範例 ====================

# 使用 Cell 1 中定義的 Token
CHANNEL_ACCESS_TOKEN = "oZPbAQXckPCTbRPN67GNPlyG/MqToO3haMOIvWOI35PGg8ZdBYEVtOc1KdJ+zYLJjOJ8+/YGaEk4f7m6W1RavpsYIp+5k1taVZ47HYboydFvMbTQ4rxXlNGysl2q0sM79gbzVuGnzHkPL2mf9SfU1gdB04t89/1O/w1cDnyilFU="

# 建立並啟動 Bot
if __name__ == "__main__":
    bot = ReservationBot(CHANNEL_ACCESS_TOKEN)
    bot.run(port=3000, debug=True)