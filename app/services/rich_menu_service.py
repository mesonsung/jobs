"""
LINE Rich Menu 管理服務
"""
from typing import Dict, Optional, List
import os
import requests
from app.core.logger import setup_logger
from app.config import LINE_CHANNEL_ACCESS_TOKEN

# 設置 logger
logger = setup_logger(__name__)


class LineRichMenuService:
    """LINE Rich Menu 管理服務"""
    
    def __init__(self, channel_access_token: Optional[str] = None):
        self.token = channel_access_token or LINE_CHANNEL_ACCESS_TOKEN
        self.base_url = "https://api.line.me/v2/bot"
    
    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """取得 API 請求標頭"""
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers
    
    def create_rich_menu(self, rich_menu_data: Dict) -> Optional[str]:
        """
        建立 Rich Menu
        
        參數:
            rich_menu_data: Rich Menu 資料（包含 size, selected, name, chatBarText, areas）
        
        返回:
            str: Rich Menu ID，如果失敗則返回 None
        """
        try:
            url = f"{self.base_url}/richmenu"
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=rich_menu_data,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            rich_menu_id = result.get("richMenuId")
            logger.info(f"成功建立 Rich Menu: {rich_menu_id}")
            return rich_menu_id
        except requests.exceptions.RequestException as e:
            logger.error(f"建立 Rich Menu 失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            return None
    
    def upload_rich_menu_image(self, rich_menu_id: str, image_path: str) -> bool:
        """
        上傳 Rich Menu 圖片
        
        參數:
            rich_menu_id: Rich Menu ID
            image_path: 圖片檔案路徑
        
        返回:
            bool: 是否成功
        """
        try:
            # LINE Rich Menu 圖片上傳使用 api-data.line.me
            data_url = "https://api-data.line.me/v2/bot"
            url = f"{data_url}/richmenu/{rich_menu_id}/content"
            
            # 判斷圖片格式
            image_ext = os.path.splitext(image_path)[1].lower()
            if image_ext in ['.jpg', '.jpeg']:
                content_type = 'image/jpeg'
            elif image_ext == '.png':
                content_type = 'image/png'
            else:
                logger.error(f"不支援的圖片格式：{image_ext}")
                return False
            
            # 讀取圖片檔案
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 上傳圖片（直接放在 request body 中，不是 multipart）
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": content_type
            }
            
            response = requests.post(
                url,
                headers=headers,
                data=image_data,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"成功上傳 Rich Menu 圖片: {rich_menu_id}")
            return True
        except FileNotFoundError:
            logger.error(f"找不到圖片檔案：{image_path}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"上傳 Rich Menu 圖片失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"HTTP 狀態碼: {e.response.status_code}")
                logger.error(f"回應內容：{e.response.text}")
                try:
                    error_json = e.response.json()
                    logger.error(f"錯誤詳情：{error_json}")
                except:
                    pass
            return False
    
    def set_default_rich_menu(self, rich_menu_id: str) -> bool:
        """
        設定預設 Rich Menu
        
        參數:
            rich_menu_id: Rich Menu ID
        
        返回:
            bool: 是否成功
        """
        try:
            url = f"{self.base_url}/user/all/richmenu/{rich_menu_id}"
            response = requests.post(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"成功設定預設 Rich Menu: {rich_menu_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"設定預設 Rich Menu 失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            return False
    
    def set_user_rich_menu(self, user_id: str, rich_menu_id: str) -> bool:
        """
        為特定用戶設定 Rich Menu
        
        參數:
            user_id: LINE User ID
            rich_menu_id: Rich Menu ID
        
        返回:
            bool: 是否成功
        """
        try:
            url = f"{self.base_url}/user/{user_id}/richmenu/{rich_menu_id}"
            logger.debug(f"設定用戶 Rich Menu: URL={url}, user_id={user_id}, rich_menu_id={rich_menu_id}")
            response = requests.post(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"✅ 成功為用戶 {user_id} 設定 Rich Menu: {rich_menu_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 為用戶設定 Rich Menu 失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"HTTP 狀態碼: {e.response.status_code}")
                logger.error(f"回應內容：{e.response.text}")
            else:
                logger.error(f"請求異常詳情：{str(e)}")
            return False
    
    def delete_user_rich_menu(self, user_id: str) -> bool:
        """
        刪除用戶的 Rich Menu
        
        參數:
            user_id: LINE User ID
        
        返回:
            bool: 是否成功
        """
        try:
            url = f"{self.base_url}/user/{user_id}/richmenu"
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"成功刪除用戶 {user_id} 的 Rich Menu")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"刪除用戶 Rich Menu 失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            return False
    
    def get_rich_menu_list(self) -> List[Dict]:
        """
        取得所有 Rich Menu 列表
        
        返回:
            List[Dict]: Rich Menu 列表
        """
        try:
            url = f"{self.base_url}/richmenu/list"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            rich_menus = result.get("richmenus", [])
            logger.info(f"取得 {len(rich_menus)} 個 Rich Menu")
            return rich_menus
        except requests.exceptions.RequestException as e:
            logger.error(f"取得 Rich Menu 列表失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            return []
    
    def get_rich_menu(self, rich_menu_id: str) -> Optional[Dict]:
        """
        取得 Rich Menu 詳細資訊
        
        參數:
            rich_menu_id: Rich Menu ID
        
        返回:
            Dict: Rich Menu 詳細資訊，如果失敗則返回 None
        """
        try:
            url = f"{self.base_url}/richmenu/{rich_menu_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"取得 Rich Menu 詳細資訊失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            return None
    
    def delete_rich_menu(self, rich_menu_id: str) -> bool:
        """
        刪除 Rich Menu
        
        參數:
            rich_menu_id: Rich Menu ID
        
        返回:
            bool: 是否成功
        """
        try:
            url = f"{self.base_url}/richmenu/{rich_menu_id}"
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"成功刪除 Rich Menu: {rich_menu_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"刪除 Rich Menu 失敗：{e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"回應內容：{e.response.text}")
            return False
    
    def get_registered_user_rich_menu_data(self) -> Dict:
        """
        取得註冊用戶的 Rich Menu 資料結構
        
        返回:
            Dict: Rich Menu 資料
        """
        return {
            "size": {
                "width": 2500,
                "height": 843
            },
            "selected": True,
            "name": "已註冊用戶 Rich Menu",
            "chatBarText": "選單",
            "areas": [
                {
                    "bounds": {
                        "x": 0,
                        "y": 0,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "action=view_profile&step=view",
                        "label": "檢視註冊資料"
                    }
                },
                {
                    "bounds": {
                        "x": 833,
                        "y": 0,
                        "width": 833,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "action=job&step=list",
                        "label": "可報班工作"
                    }
                },
                {
                    "bounds": {
                        "x": 1666,
                        "y": 0,
                        "width": 834,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "action=job&step=my_applications",
                        "label": "已報班記錄"
                    }
                }
            ]
        }
    
    def get_unregistered_user_rich_menu_data(self) -> Dict:
        """
        取得未註冊用戶的 Rich Menu 資料結構
        
        返回:
            Dict: Rich Menu 資料
        """
        return {
            "size": {
                "width": 2500,
                "height": 843
            },
            "selected": True,
            "name": "未註冊用戶 Rich Menu",
            "chatBarText": "選單",
            "areas": [
                {
                    "bounds": {
                        "x": 0,
                        "y": 0,
                        "width": 1250,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "action=register&step=register",
                        "label": "註冊功能"
                    }
                },
                {
                    "bounds": {
                        "x": 1250,
                        "y": 0,
                        "width": 1250,
                        "height": 843
                    },
                    "action": {
                        "type": "postback",
                        "data": "action=job&step=list",
                        "label": "可報班工作"
                    }
                }
            ]
        }
