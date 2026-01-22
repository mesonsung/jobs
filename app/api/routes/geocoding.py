"""
地理編碼相關 API 路由
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.services.geocoding_service import GeocodingService
from app.api.dependencies import get_current_active_user
from app.models.schemas import UserInDB
from typing import Annotated
from fastapi import Depends

router = APIRouter(prefix="/api/geocode", tags=["地理編碼"])

# 創建全域 GeocodingService 實例
_geocoding_service_instance = None

def get_geocoding_service() -> GeocodingService:
    """取得 GeocodingService 實例（單例模式）"""
    global _geocoding_service_instance
    if _geocoding_service_instance is None:
        from app.config import GOOGLE_MAPS_API_KEY
        _geocoding_service_instance = GeocodingService(api_key=GOOGLE_MAPS_API_KEY)
    return _geocoding_service_instance


class GeocodeRequest(BaseModel):
    """地理編碼請求"""
    address: str = Field(..., description="地址")


class GeocodeResponse(BaseModel):
    """地理編碼回應"""
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    success: bool
    message: Optional[str] = None


class ReverseGeocodeRequest(BaseModel):
    """反向地理編碼請求"""
    latitude: float = Field(..., description="緯度")
    longitude: float = Field(..., description="經度")


class ReverseGeocodeResponse(BaseModel):
    """反向地理編碼回應"""
    latitude: float
    longitude: float
    address: Optional[str] = None
    success: bool
    message: Optional[str] = None


@router.post("", response_model=GeocodeResponse)
def geocode_address(
    request: GeocodeRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    geocoding_service: Annotated[GeocodingService, Depends(get_geocoding_service)]
):
    """根據地址取得經緯度座標（需要認證）"""
    coordinates = geocoding_service.get_coordinates(request.address)
    
    if coordinates:
        latitude, longitude = coordinates
        return GeocodeResponse(
            address=request.address,
            latitude=latitude,
            longitude=longitude,
            success=True,
            message="成功取得座標"
        )
    else:
        return GeocodeResponse(
            address=request.address,
            latitude=None,
            longitude=None,
            success=False,
            message="無法取得座標，請檢查地址或 Google Maps API Key 設定"
        )


@router.post("/reverse", response_model=ReverseGeocodeResponse)
def reverse_geocode(
    request: ReverseGeocodeRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    geocoding_service: Annotated[GeocodingService, Depends(get_geocoding_service)]
):
    """根據經緯度取得地址（反向地理編碼，需要認證）"""
    address = geocoding_service.get_address_from_coordinates(
        request.latitude,
        request.longitude
    )
    
    if address:
        return ReverseGeocodeResponse(
            latitude=request.latitude,
            longitude=request.longitude,
            address=address,
            success=True,
            message="成功取得地址"
        )
    else:
        return ReverseGeocodeResponse(
            latitude=request.latitude,
            longitude=request.longitude,
            address=None,
            success=False,
            message="無法取得地址，請檢查座標或 Google Maps API Key 設定"
        )
