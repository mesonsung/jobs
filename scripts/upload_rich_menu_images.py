#!/usr/bin/env python3
"""
重新上傳 Rich Menu 圖片到 LINE 官方帳號

此腳本會：
1. 重新生成 Rich Menu 樣本圖片（如果圖片不存在或需要更新）
2. 上傳圖片到現有的 Rich Menu（使用環境變數中的 Rich Menu ID）
3. 如果環境變數未設定，會列出所有 Rich Menu 供選擇
"""
import os
import sys

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rich_menu_service import LineRichMenuService
from app.services.auth_service import AuthService
from app.config import REGISTERED_USER_RICH_MENU_ID, UNREGISTERED_USER_RICH_MENU_ID
from app.core.logger import setup_logger

# 設置 logger
logger = setup_logger(__name__)


def update_all_users_rich_menu(rich_menu_service: LineRichMenuService, rich_menu_id: str, is_registered: bool = True):
    """
    更新所有用戶的 Rich Menu
    
    參數:
        rich_menu_service: Rich Menu 服務實例
        rich_menu_id: 新的 Rich Menu ID
        is_registered: 是否為已註冊用戶的 Rich Menu
    """
    try:
        auth_service = AuthService()
        line_user_ids = auth_service.get_all_line_users()
        
        if not line_user_ids:
            print(f"   ℹ️  沒有找到已註冊的 LINE 用戶")
            return
        
        print(f"   📋 找到 {len(line_user_ids)} 個已註冊的 LINE 用戶")
        
        success_count = 0
        fail_count = 0
        
        for i, user_id in enumerate(line_user_ids, 1):
            try:
                success = rich_menu_service.set_user_rich_menu(user_id, rich_menu_id)
                if success:
                    success_count += 1
                    if i % 10 == 0 or i == len(line_user_ids):
                        print(f"   📊 進度: {i}/{len(line_user_ids)} ({success_count} 成功, {fail_count} 失敗)")
                else:
                    fail_count += 1
                    logger.warning(f"為用戶 {user_id} 設定 Rich Menu 失敗")
            except Exception as e:
                fail_count += 1
                logger.error(f"為用戶 {user_id} 設定 Rich Menu 時發生錯誤：{e}")
        
        print(f"   ✅ 更新完成: {success_count} 成功, {fail_count} 失敗")
        
        if fail_count > 0:
            print(f"   ⚠️  有 {fail_count} 個用戶的 Rich Menu 更新失敗，請檢查日誌")
    except Exception as e:
        logger.error(f"更新所有用戶 Rich Menu 時發生錯誤：{e}", exc_info=True)
        print(f"   ❌ 更新所有用戶 Rich Menu 時發生錯誤：{e}")


def generate_images_if_needed():
    """如果需要，重新生成 Rich Menu 圖片"""
    print("📋 檢查 Rich Menu 圖片...")
    
    registered_image_path = "rich_menu_samples/rich_menu_registered.jpg"
    unregistered_image_path = "rich_menu_samples/rich_menu_unregistered.jpg"
    
    # 檢查圖片是否存在
    need_generate = False
    if not os.path.exists(registered_image_path):
        print(f"⚠️  找不到已註冊用戶的圖片：{registered_image_path}")
        need_generate = True
    if not os.path.exists(unregistered_image_path):
        print(f"⚠️  找不到未註冊用戶的圖片：{unregistered_image_path}")
        need_generate = True
    
    if need_generate:
        print("\n🔄 重新生成 Rich Menu 圖片...")
        try:
            # 導入並執行生成腳本
            import subprocess
            result = subprocess.run(
                [sys.executable, "scripts/generate_rich_menu_samples.py"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Rich Menu 圖片生成成功")
            else:
                print(f"❌ Rich Menu 圖片生成失敗：{result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 執行生成腳本時發生錯誤：{e}")
            return False
    else:
        print("✅ Rich Menu 圖片已存在")
    
    return True


def upload_rich_menu_images():
    """上傳 Rich Menu 圖片到 LINE 官方帳號"""
    print("=" * 60)
    print("重新上傳 Rich Menu 圖片到 LINE 官方帳號")
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
    
    # 1. 處理已註冊用戶的 Rich Menu
    registered_rich_menu_id = REGISTERED_USER_RICH_MENU_ID
    
    if not registered_rich_menu_id:
        print("\n⚠️  環境變數 REGISTERED_USER_RICH_MENU_ID 未設定")
        print("   嘗試從 Rich Menu 列表中查找...")
        try:
            rich_menus = rich_menu_service.get_rich_menu_list()
            for rm in rich_menus:
                rm_id = rm.get('richMenuId')
                rm_name = rm.get('name', '')
                if rm_name == '已註冊用戶 Rich Menu':
                    registered_rich_menu_id = rm_id
                    print(f"   ✅ 找到已註冊用戶的 Rich Menu: {registered_rich_menu_id}")
                    break
            
            # 如果還是沒找到，透過詳細資訊查找
            if not registered_rich_menu_id:
                print("   透過 name 欄位未找到，嘗試透過詳細資訊查找...")
                for rm in rich_menus:
                    rm_id = rm.get('richMenuId')
                    if not rm_id or not isinstance(rm_id, str):
                        continue
                    try:
                        rm_detail = rich_menu_service.get_rich_menu(rm_id)
                        if rm_detail:
                            areas = rm_detail.get('areas', [])
                            if len(areas) == 3:
                                has_my_applications = any(
                                    area.get('action', {}).get('data', '').endswith('my_applications')
                                    for area in areas
                                )
                                if has_my_applications:
                                    registered_rich_menu_id = rm_id
                                    print(f"   ✅ 透過詳細資訊找到已註冊用戶的 Rich Menu: {registered_rich_menu_id}")
                                    break
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"   ❌ 查找 Rich Menu 列表時發生錯誤：{e}")
    
    if registered_rich_menu_id:
        print(f"\n📤 更新已註冊用戶的 Rich Menu 圖片...")
        print(f"   Rich Menu ID: {registered_rich_menu_id}")
        print(f"   圖片路徑: {registered_image_path}")
        
        # 嘗試上傳圖片
        upload_success = rich_menu_service.upload_rich_menu_image(registered_rich_menu_id, registered_image_path)
        
        if not upload_success:
            # 如果上傳失敗，可能是因為圖片已存在，需要重新建立 Rich Menu
            print(f"   ⚠️  上傳失敗，可能是因為圖片已存在")
            print(f"   🔄 嘗試重新建立 Rich Menu...")
            
            # 取得 Rich Menu 資料
            registered_rich_menu_data = rich_menu_service.get_registered_user_rich_menu_data()
            
            # 刪除舊的 Rich Menu
            print(f"   🗑️  刪除舊的 Rich Menu...")
            if rich_menu_service.delete_rich_menu(registered_rich_menu_id):
                print(f"   ✅ 已刪除舊的 Rich Menu")
            else:
                print(f"   ⚠️  刪除舊的 Rich Menu 失敗，嘗試繼續...")
            
            # 建立新的 Rich Menu
            print(f"   📋 建立新的 Rich Menu...")
            new_registered_rich_menu_id = rich_menu_service.create_rich_menu(registered_rich_menu_data)
            
            if not new_registered_rich_menu_id:
                print(f"   ❌ 建立新的 Rich Menu 失敗")
                return False
            
            print(f"   ✅ 已建立新的 Rich Menu: {new_registered_rich_menu_id}")
            registered_rich_menu_id = new_registered_rich_menu_id
            
            # 上傳圖片到新的 Rich Menu
            print(f"   📤 上傳圖片到新的 Rich Menu...")
            if rich_menu_service.upload_rich_menu_image(registered_rich_menu_id, registered_image_path):
                print(f"   ✅ 已成功上傳已註冊用戶的 Rich Menu 圖片")
                print(f"\n   💡 新的 Rich Menu ID: {registered_rich_menu_id}")
                print(f"   請更新 .env 檔案中的 REGISTERED_USER_RICH_MENU_ID")
                
                # 自動更新所有已註冊用戶的 Rich Menu
                print(f"\n   🔄 自動更新所有已註冊用戶的 Rich Menu...")
                update_all_users_rich_menu(rich_menu_service, registered_rich_menu_id, is_registered=True)
            else:
                print(f"   ❌ 上傳圖片失敗")
                # 清理：刪除新建立的 Rich Menu
                rich_menu_service.delete_rich_menu(registered_rich_menu_id)
                return False
        else:
            print(f"✅ 已成功更新已註冊用戶的 Rich Menu 圖片")
            # 即使沒有重新建立，也更新所有用戶的 Rich Menu（確保一致性）
            print(f"\n   🔄 自動更新所有已註冊用戶的 Rich Menu...")
            update_all_users_rich_menu(rich_menu_service, registered_rich_menu_id, is_registered=True)
    else:
        print("\n⚠️  未找到已註冊用戶的 Rich Menu，跳過上傳")
        print("   提示：可以在 .env 檔案中設定 REGISTERED_USER_RICH_MENU_ID")
    
    # 2. 處理未註冊用戶的 Rich Menu
    unregistered_rich_menu_id = UNREGISTERED_USER_RICH_MENU_ID
    
    if not unregistered_rich_menu_id:
        print("\n⚠️  環境變數 UNREGISTERED_USER_RICH_MENU_ID 未設定")
        print("   嘗試從 Rich Menu 列表中查找...")
        try:
            rich_menus = rich_menu_service.get_rich_menu_list()
            for rm in rich_menus:
                rm_id = rm.get('richMenuId')
                rm_name = rm.get('name', '')
                if rm_name == '未註冊用戶 Rich Menu':
                    unregistered_rich_menu_id = rm_id
                    print(f"   ✅ 找到未註冊用戶的 Rich Menu: {unregistered_rich_menu_id}")
                    break
            
            # 如果還是沒找到，透過詳細資訊查找
            if not unregistered_rich_menu_id:
                print("   透過 name 欄位未找到，嘗試透過詳細資訊查找...")
                for rm in rich_menus:
                    rm_id = rm.get('richMenuId')
                    if not rm_id or not isinstance(rm_id, str):
                        continue
                    try:
                        rm_detail = rich_menu_service.get_rich_menu(rm_id)
                        if rm_detail:
                            areas = rm_detail.get('areas', [])
                            if len(areas) == 2:
                                has_register = any(
                                    'action=register' in area.get('action', {}).get('data', '')
                                    for area in areas
                                )
                                if has_register:
                                    unregistered_rich_menu_id = rm_id
                                    print(f"   ✅ 透過詳細資訊找到未註冊用戶的 Rich Menu: {unregistered_rich_menu_id}")
                                    break
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"   ❌ 查找 Rich Menu 列表時發生錯誤：{e}")
    
    if unregistered_rich_menu_id:
        print(f"\n📤 更新未註冊用戶的 Rich Menu 圖片...")
        print(f"   Rich Menu ID: {unregistered_rich_menu_id}")
        print(f"   圖片路徑: {unregistered_image_path}")
        
        # 嘗試上傳圖片
        upload_success = rich_menu_service.upload_rich_menu_image(unregistered_rich_menu_id, unregistered_image_path)
        
        if not upload_success:
            # 如果上傳失敗，可能是因為圖片已存在，需要重新建立 Rich Menu
            print(f"   ⚠️  上傳失敗，可能是因為圖片已存在")
            print(f"   🔄 嘗試重新建立 Rich Menu...")
            
            # 取得 Rich Menu 資料
            unregistered_rich_menu_data = rich_menu_service.get_unregistered_user_rich_menu_data()
            
            # 檢查是否為預設 Rich Menu
            is_default = False
            try:
                # 嘗試取得預設 Rich Menu ID（如果有的話）
                # 注意：LINE API 沒有直接取得預設 Rich Menu 的方法
                # 我們假設如果這是未註冊用戶的 Rich Menu，可能是預設的
                is_default = True
            except:
                pass
            
            # 刪除舊的 Rich Menu
            print(f"   🗑️  刪除舊的 Rich Menu...")
            if rich_menu_service.delete_rich_menu(unregistered_rich_menu_id):
                print(f"   ✅ 已刪除舊的 Rich Menu")
            else:
                print(f"   ⚠️  刪除舊的 Rich Menu 失敗，嘗試繼續...")
            
            # 建立新的 Rich Menu
            print(f"   📋 建立新的 Rich Menu...")
            new_unregistered_rich_menu_id = rich_menu_service.create_rich_menu(unregistered_rich_menu_data)
            
            if not new_unregistered_rich_menu_id:
                print(f"   ❌ 建立新的 Rich Menu 失敗")
                return False
            
            print(f"   ✅ 已建立新的 Rich Menu: {new_unregistered_rich_menu_id}")
            unregistered_rich_menu_id = new_unregistered_rich_menu_id
            
            # 上傳圖片到新的 Rich Menu
            print(f"   📤 上傳圖片到新的 Rich Menu...")
            if rich_menu_service.upload_rich_menu_image(unregistered_rich_menu_id, unregistered_image_path):
                print(f"   ✅ 已成功上傳未註冊用戶的 Rich Menu 圖片")
                
                # 如果原本是預設 Rich Menu，設定新的為預設
                if is_default:
                    print(f"   🔧 設定新的 Rich Menu 為預設...")
                    if rich_menu_service.set_default_rich_menu(unregistered_rich_menu_id):
                        print(f"   ✅ 已設定為預設 Rich Menu")
                    else:
                        print(f"   ⚠️  設定預設 Rich Menu 失敗")
                
                print(f"\n   💡 新的 Rich Menu ID: {unregistered_rich_menu_id}")
                print(f"   請更新 .env 檔案中的 UNREGISTERED_USER_RICH_MENU_ID")
            else:
                print(f"   ❌ 上傳圖片失敗")
                # 清理：刪除新建立的 Rich Menu
                rich_menu_service.delete_rich_menu(unregistered_rich_menu_id)
                return False
        else:
            print(f"✅ 已成功更新未註冊用戶的 Rich Menu 圖片")
            # 未註冊用戶會自動看到預設 Rich Menu，無需手動更新
    else:
        print("\n⚠️  未找到未註冊用戶的 Rich Menu，跳過上傳")
        print("   提示：可以在 .env 檔案中設定 UNREGISTERED_USER_RICH_MENU_ID")
    
    # 3. 顯示結果
    print("\n" + "=" * 60)
    print("✅ Rich Menu 圖片上傳完成！")
    print("=" * 60)
    
    if registered_rich_menu_id:
        print(f"\n📋 已註冊用戶 Rich Menu:")
        print(f"   ID: {registered_rich_menu_id}")
        print(f"   狀態: ✅ 圖片已更新")
    
    if unregistered_rich_menu_id:
        print(f"\n📋 未註冊用戶 Rich Menu:")
        print(f"   ID: {unregistered_rich_menu_id}")
        print(f"   狀態: ✅ 圖片已更新")
    
    print("\n💡 提示:")
    print("   - 圖片更新後，用戶可能需要重新開啟 LINE 才能看到新的 Rich Menu")
    print("   - 如果環境變數未設定，系統會自動查找對應的 Rich Menu")
    if registered_rich_menu_id and registered_rich_menu_id != REGISTERED_USER_RICH_MENU_ID:
        print(f"   - ⚠️  已註冊用戶的 Rich Menu ID 已變更，請更新 .env 檔案")
    if unregistered_rich_menu_id and unregistered_rich_menu_id != UNREGISTERED_USER_RICH_MENU_ID:
        print(f"   - ⚠️  未註冊用戶的 Rich Menu ID 已變更，請更新 .env 檔案")
    print()
    
    return True


def main():
    """主函數"""
    try:
        # 1. 檢查並生成圖片（如果需要）
        if not generate_images_if_needed():
            print("❌ 圖片生成失敗，請檢查錯誤訊息")
            sys.exit(1)
        
        # 2. 上傳圖片
        success = upload_rich_menu_images()
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
