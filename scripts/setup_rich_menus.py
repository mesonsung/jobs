#!/usr/bin/env python3
"""
建立並上傳 Rich Menu 到 LINE 官方帳號

此腳本會：
1. 建立已註冊用戶的 Rich Menu
2. 建立未註冊用戶的 Rich Menu
3. 上傳對應的圖片
4. 設定未註冊用戶的 Rich Menu 為預設
"""
import os
import sys

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rich_menu_service import LineRichMenuService
from app.core.logger import setup_logger

# 設置 logger
logger = setup_logger(__name__)


def setup_rich_menus():
    """建立並上傳 Rich Menu 到 LINE 官方帳號"""
    print("=" * 60)
    print("開始建立並上傳 Rich Menu 到 LINE 官方帳號")
    print("=" * 60)
    
    # 初始化 Rich Menu 服務
    rich_menu_service = LineRichMenuService()
    
    # 圖片路徑
    registered_image_path = "rich_menu_samples/rich_menu_registered.jpg"
    unregistered_image_path = "rich_menu_samples/rich_menu_unregistered.jpg"
    
    # 檢查圖片是否存在
    if not os.path.exists(registered_image_path):
        print(f"❌ 錯誤：找不到已註冊用戶的圖片：{registered_image_path}")
        print("   請先執行 scripts/generate_rich_menu_samples.py 生成圖片")
        return False
    
    if not os.path.exists(unregistered_image_path):
        print(f"❌ 錯誤：找不到未註冊用戶的圖片：{unregistered_image_path}")
        print("   請先執行 scripts/generate_rich_menu_samples.py 生成圖片")
        return False
    
    # 1. 建立已註冊用戶的 Rich Menu
    print("\n📋 步驟 1: 建立已註冊用戶的 Rich Menu...")
    registered_rich_menu_data = rich_menu_service.get_registered_user_rich_menu_data()
    registered_rich_menu_id = rich_menu_service.create_rich_menu(registered_rich_menu_data)
    
    if not registered_rich_menu_id:
        print("❌ 建立已註冊用戶的 Rich Menu 失敗")
        return False
    
    print(f"✅ 已建立已註冊用戶的 Rich Menu: {registered_rich_menu_id}")
    
    # 上傳已註冊用戶的圖片
    print("📤 上傳已註冊用戶的 Rich Menu 圖片...")
    if rich_menu_service.upload_rich_menu_image(registered_rich_menu_id, registered_image_path):
        print(f"✅ 已上傳已註冊用戶的 Rich Menu 圖片")
    else:
        print(f"❌ 上傳已註冊用戶的 Rich Menu 圖片失敗")
        # 刪除已建立的 Rich Menu
        rich_menu_service.delete_rich_menu(registered_rich_menu_id)
        return False
    
    # 2. 建立未註冊用戶的 Rich Menu
    print("\n📋 步驟 2: 建立未註冊用戶的 Rich Menu...")
    unregistered_rich_menu_data = rich_menu_service.get_unregistered_user_rich_menu_data()
    unregistered_rich_menu_id = rich_menu_service.create_rich_menu(unregistered_rich_menu_data)
    
    if not unregistered_rich_menu_id:
        print("❌ 建立未註冊用戶的 Rich Menu 失敗")
        return False
    
    print(f"✅ 已建立未註冊用戶的 Rich Menu: {unregistered_rich_menu_id}")
    
    # 上傳未註冊用戶的圖片
    print("📤 上傳未註冊用戶的 Rich Menu 圖片...")
    if rich_menu_service.upload_rich_menu_image(unregistered_rich_menu_id, unregistered_image_path):
        print(f"✅ 已上傳未註冊用戶的 Rich Menu 圖片")
    else:
        print(f"❌ 上傳未註冊用戶的 Rich Menu 圖片失敗")
        # 刪除已建立的 Rich Menu
        rich_menu_service.delete_rich_menu(unregistered_rich_menu_id)
        return False
    
    # 3. 設定未註冊用戶的 Rich Menu 為預設
    print("\n📋 步驟 3: 設定未註冊用戶的 Rich Menu 為預設...")
    if rich_menu_service.set_default_rich_menu(unregistered_rich_menu_id):
        print(f"✅ 已設定未註冊用戶的 Rich Menu 為預設")
    else:
        print(f"⚠️  設定預設 Rich Menu 失敗，但 Rich Menu 已建立")
    
    # 4. 顯示結果
    print("\n" + "=" * 60)
    print("✅ Rich Menu 建立完成！")
    print("=" * 60)
    print(f"\n📋 Rich Menu ID:")
    print(f"   已註冊用戶: {registered_rich_menu_id}")
    print(f"   未註冊用戶: {unregistered_rich_menu_id} (預設)")
    print(f"\n💡 提示:")
    print(f"   - 所有新用戶將看到未註冊用戶的 Rich Menu")
    print(f"   - 當用戶註冊後，系統會自動為該用戶設定已註冊用戶的 Rich Menu")
    print(f"\n📝 環境變數設定（可選）:")
    print(f"   在 .env 檔案中添加以下設定，可確保自動設定功能正常運作：")
    print(f"   REGISTERED_USER_RICH_MENU_ID={registered_rich_menu_id}")
    print(f"   UNREGISTERED_USER_RICH_MENU_ID={unregistered_rich_menu_id}")
    print(f"\n   或者系統會自動從 Rich Menu 列表中查找對應的 Rich Menu")
    print()
    
    return True


def main():
    """主函數"""
    try:
        success = setup_rich_menus()
        if success:
            print("✅ 所有操作完成！")
            sys.exit(0)
        else:
            print("❌ 操作失敗，請檢查錯誤訊息")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
    except Exception as e:
        logger.error(f"發生錯誤：{e}", exc_info=True)
        print(f"\n❌ 發生錯誤：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
