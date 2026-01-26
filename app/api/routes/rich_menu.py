"""
LINE Rich Menu 管理 API 路由
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Annotated

from app.services.rich_menu_service import LineRichMenuService
from app.api.dependencies import get_current_active_user, require_admin
from app.models.schemas import UserInDB

router = APIRouter(prefix="/api/rich-menu", tags=["Rich Menu 管理"])

# 創建服務實例（單例模式）
_rich_menu_service_instance = None

def get_rich_menu_service() -> LineRichMenuService:
    """取得 LineRichMenuService 實例"""
    global _rich_menu_service_instance
    if _rich_menu_service_instance is None:
        _rich_menu_service_instance = LineRichMenuService()
    return _rich_menu_service_instance


class RichMenuCreateRequest(BaseModel):
    """建立 Rich Menu 請求"""
    menu_type: str = Field(..., description="Rich Menu 類型：'registered' (已註冊用戶) 或 'unregistered' (未註冊用戶)")
    image_path: Optional[str] = Field(None, description="圖片檔案路徑（可選，如果提供則會上傳）")


class RichMenuSetRequest(BaseModel):
    """設定 Rich Menu 請求"""
    rich_menu_id: str = Field(..., description="Rich Menu ID")
    user_id: Optional[str] = Field(None, description="用戶 ID（可選，如果不提供則設定為預設）")


class RichMenuDeleteRequest(BaseModel):
    """刪除 Rich Menu 請求"""
    rich_menu_id: str = Field(..., description="Rich Menu ID")


@router.post("/create/registered", summary="建立已註冊用戶的 Rich Menu")
async def create_registered_user_rich_menu(
    image_path: Optional[str] = Form(None, description="圖片檔案路徑"),
    image_file: Optional[UploadFile] = File(None, description="圖片檔案（可選）"),
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    建立已註冊用戶的 Rich Menu
    
    需要管理員權限
    """
    try:
        # 取得 Rich Menu 資料結構
        rich_menu_data = rich_menu_service.get_registered_user_rich_menu_data()
        
        # 建立 Rich Menu
        rich_menu_id = rich_menu_service.create_rich_menu(rich_menu_data)
        if not rich_menu_id:
            raise HTTPException(status_code=500, detail="建立 Rich Menu 失敗")
        
        # 如果有提供圖片，上傳圖片
        if image_file:
            # 保存上傳的檔案到臨時位置
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(await image_file.read())
                tmp_path = tmp_file.name
            
            try:
                success = rich_menu_service.upload_rich_menu_image(rich_menu_id, tmp_path)
                if not success:
                    # 如果上傳失敗，刪除已建立的 Rich Menu
                    rich_menu_service.delete_rich_menu(rich_menu_id)
                    raise HTTPException(status_code=500, detail="上傳 Rich Menu 圖片失敗")
            finally:
                # 清理臨時檔案
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        elif image_path:
            success = rich_menu_service.upload_rich_menu_image(rich_menu_id, image_path)
            if not success:
                # 如果上傳失敗，刪除已建立的 Rich Menu
                rich_menu_service.delete_rich_menu(rich_menu_id)
                raise HTTPException(status_code=500, detail="上傳 Rich Menu 圖片失敗")
        
        return {
            "success": True,
            "rich_menu_id": rich_menu_id,
            "message": "已註冊用戶 Rich Menu 建立成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立 Rich Menu 時發生錯誤：{str(e)}")


@router.post("/create/unregistered", summary="建立未註冊用戶的 Rich Menu")
async def create_unregistered_user_rich_menu(
    image_path: Optional[str] = Form(None, description="圖片檔案路徑"),
    image_file: Optional[UploadFile] = File(None, description="圖片檔案（可選）"),
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    建立未註冊用戶的 Rich Menu
    
    需要管理員權限
    """
    try:
        # 取得 Rich Menu 資料結構
        rich_menu_data = rich_menu_service.get_unregistered_user_rich_menu_data()
        
        # 建立 Rich Menu
        rich_menu_id = rich_menu_service.create_rich_menu(rich_menu_data)
        if not rich_menu_id:
            raise HTTPException(status_code=500, detail="建立 Rich Menu 失敗")
        
        # 如果有提供圖片，上傳圖片
        if image_file:
            # 保存上傳的檔案到臨時位置
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(await image_file.read())
                tmp_path = tmp_file.name
            
            try:
                success = rich_menu_service.upload_rich_menu_image(rich_menu_id, tmp_path)
                if not success:
                    # 如果上傳失敗，刪除已建立的 Rich Menu
                    rich_menu_service.delete_rich_menu(rich_menu_id)
                    raise HTTPException(status_code=500, detail="上傳 Rich Menu 圖片失敗")
            finally:
                # 清理臨時檔案
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        elif image_path:
            success = rich_menu_service.upload_rich_menu_image(rich_menu_id, image_path)
            if not success:
                # 如果上傳失敗，刪除已建立的 Rich Menu
                rich_menu_service.delete_rich_menu(rich_menu_id)
                raise HTTPException(status_code=500, detail="上傳 Rich Menu 圖片失敗")
        
        return {
            "success": True,
            "rich_menu_id": rich_menu_id,
            "message": "未註冊用戶 Rich Menu 建立成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立 Rich Menu 時發生錯誤：{str(e)}")


@router.post("/set-default", summary="設定預設 Rich Menu")
def set_default_rich_menu(
    request: RichMenuSetRequest,
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    設定預設 Rich Menu（所有用戶都會看到）
    
    需要管理員權限
    """
    success = rich_menu_service.set_default_rich_menu(request.rich_menu_id)
    if not success:
        raise HTTPException(status_code=500, detail="設定預設 Rich Menu 失敗")
    
    return {
        "success": True,
        "message": "預設 Rich Menu 設定成功"
    }


@router.post("/set-user", summary="為特定用戶設定 Rich Menu")
def set_user_rich_menu(
    request: RichMenuSetRequest,
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    為特定用戶設定 Rich Menu
    
    需要管理員權限
    """
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id 是必需的")
    
    success = rich_menu_service.set_user_rich_menu(request.user_id, request.rich_menu_id)
    if not success:
        raise HTTPException(status_code=500, detail="為用戶設定 Rich Menu 失敗")
    
    return {
        "success": True,
        "message": f"用戶 {request.user_id} 的 Rich Menu 設定成功"
    }


@router.get("/list", summary="取得所有 Rich Menu 列表")
def get_rich_menu_list(
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    取得所有 Rich Menu 列表
    
    需要管理員權限
    """
    rich_menus = rich_menu_service.get_rich_menu_list()
    return {
        "success": True,
        "rich_menus": rich_menus,
        "count": len(rich_menus)
    }


@router.get("/{rich_menu_id}", summary="取得 Rich Menu 詳細資訊")
def get_rich_menu(
    rich_menu_id: str,
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    取得 Rich Menu 詳細資訊
    
    需要管理員權限
    """
    rich_menu = rich_menu_service.get_rich_menu(rich_menu_id)
    if not rich_menu:
        raise HTTPException(status_code=404, detail="找不到指定的 Rich Menu")
    
    return {
        "success": True,
        "rich_menu": rich_menu
    }


@router.delete("/{rich_menu_id}", summary="刪除 Rich Menu")
def delete_rich_menu(
    rich_menu_id: str,
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    刪除 Rich Menu
    
    需要管理員權限
    """
    success = rich_menu_service.delete_rich_menu(rich_menu_id)
    if not success:
        raise HTTPException(status_code=500, detail="刪除 Rich Menu 失敗")
    
    return {
        "success": True,
        "message": "Rich Menu 刪除成功"
    }


@router.delete("/user/{user_id}", summary="刪除用戶的 Rich Menu")
def delete_user_rich_menu(
    user_id: str,
    current_user: Annotated[UserInDB, Depends(require_admin)] = None,
    rich_menu_service: Annotated[LineRichMenuService, Depends(get_rich_menu_service)] = None
):
    """
    刪除特定用戶的 Rich Menu
    
    需要管理員權限
    """
    success = rich_menu_service.delete_user_rich_menu(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="刪除用戶 Rich Menu 失敗")
    
    return {
        "success": True,
        "message": f"用戶 {user_id} 的 Rich Menu 刪除成功"
    }
