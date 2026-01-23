"""
Google Maps Geocoding 服務
"""
import os
from typing import Optional, Tuple
import requests

from app.config import GOOGLE_MAPS_API_KEY
from app.core.logger import setup_logger

# 設置 logger
logger = setup_logger(__name__)


class GeocodingService:
    """Google Maps Geocoding 服務"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化地理編碼服務
        
        參數:
            api_key: Google Maps API Key（可選，未提供時使用配置中的預設值）
        """
        self.api_key = api_key or GOOGLE_MAPS_API_KEY
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def get_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """
        根據地址取得經緯度座標
        
        參數:
            address: 地址字串
        
        返回:
            Optional[Tuple[float, float]]: (緯度, 經度) 或 None（如果失敗）
        """
        if not self.api_key:
            logger.warning("未設定 GOOGLE_MAPS_API_KEY，無法取得座標")
            return None
        
        try:
            params = {
                "address": address,
                "key": self.api_key,
                "language": "zh-TW"  # 使用繁體中文
            }
            
            response = requests.get(self.geocoding_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                latitude = location.get("lat")
                longitude = location.get("lng")
                
                if latitude and longitude:
                    logger.debug(f"成功取得座標：{address} -> ({latitude}, {longitude})")
                    return (float(latitude), float(longitude))
                else:
                    logger.warning(f"無法從回應中取得座標：{address}")
                    return None
            else:
                status = data.get("status", "UNKNOWN")
                logger.warning(f"Geocoding API 錯誤：{status} - {address}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding API 請求錯誤：{e}", exc_info=True)
            return None
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"解析 Geocoding 回應錯誤：{e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"取得座標時發生未預期錯誤：{e}", exc_info=True)
            return None
    
    def get_address_from_coordinates(self, latitude: float, longitude: float) -> Optional[str]:
        """
        根據經緯度取得地址（反向地理編碼）
        
        參數:
            latitude: 緯度
            longitude: 經度
        
        返回:
            Optional[str]: 地址字串或 None（如果失敗）
        """
        if not self.api_key:
            logger.warning("未設定 GOOGLE_MAPS_API_KEY，無法取得地址")
            return None
        
        try:
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self.api_key,
                "language": "zh-TW"  # 使用繁體中文
            }
            
            response = requests.get(self.geocoding_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                formatted_address = data["results"][0].get("formatted_address")
                if formatted_address:
                    logger.debug(f"成功取得地址：({latitude}, {longitude}) -> {formatted_address}")
                    return formatted_address
                else:
                    logger.warning(f"無法從回應中取得地址：({latitude}, {longitude})")
                    return None
            else:
                status = data.get("status", "UNKNOWN")
                logger.warning(f"Reverse Geocoding API 錯誤：{status} - ({latitude}, {longitude})")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Reverse Geocoding API 請求錯誤：{e}", exc_info=True)
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"解析 Reverse Geocoding 回應錯誤：{e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"取得地址時發生未預期錯誤：{e}", exc_info=True)
            return None
