#!/usr/bin/env python3
"""
測試 Rich Menu 自動設定功能
用於診斷註冊後 Rich Menu 未設定的問題
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rich_menu_service import LineRichMenuService
from app.config import REGISTERED_USER_RICH_MENU_ID, UNREGISTERED_USER_RICH_MENU_ID
from app.core.logger import setup_logger

logger = setup_logger(__name__)

def test_rich_menu_setup():
    """測試 Rich Menu 設定功能"""
    print("=" * 60)
    print("Rich Menu 自動設定功能診斷")
    print("=" * 60)
    
    # 1. 檢查環境變數
    print("\n📋 步驟 1: 檢查環境變數設定")
    print(f"   REGISTERED_USER_RICH_MENU_ID: {REGISTERED_USER_RICH_MENU_ID}")
    print(f"   UNREGISTERED_USER_RICH_MENU_ID: {UNREGISTERED_USER_RICH_MENU_ID}")
    
    if not REGISTERED_USER_RICH_MENU_ID:
        print("   ⚠️  警告: REGISTERED_USER_RICH_MENU_ID 未設定")
        print("   系統將嘗試從 Rich Menu 列表中自動查找")
    else:
        print(f"   ✅ REGISTERED_USER_RICH_MENU_ID 已設定: {REGISTERED_USER_RICH_MENU_ID}")
    
    # 2. 檢查 Rich Menu 服務
    print("\n📋 步驟 2: 檢查 Rich Menu 服務")
    try:
        rich_menu_service = LineRichMenuService()
        print("   ✅ Rich Menu 服務初始化成功")
    except Exception as e:
        print(f"   ❌ Rich Menu 服務初始化失敗: {e}")
        return False
    
    # 3. 取得 Rich Menu 列表
    print("\n📋 步驟 3: 取得 Rich Menu 列表")
    try:
        rich_menus = rich_menu_service.get_rich_menu_list()
        print(f"   ✅ 取得 {len(rich_menus)} 個 Rich Menu")
        
        if len(rich_menus) == 0:
            print("   ⚠️  警告: 沒有找到任何 Rich Menu")
            print("   請先執行 scripts/setup_rich_menus.py 建立 Rich Menu")
            return False
        
        # 顯示所有 Rich Menu
        print("\n   已建立的 Rich Menu:")
        for i, rm in enumerate(rich_menus, 1):
            rm_id = rm.get('richMenuId', 'N/A')
            rm_name = rm.get('name', 'N/A')
            print(f"   {i}. ID: {rm_id}, Name: {rm_name}")
            
            # 如果是已註冊用戶的 Rich Menu，顯示詳細資訊
            if rm_name == '已註冊用戶 Rich Menu' or rm_id == REGISTERED_USER_RICH_MENU_ID:
                print(f"      ✅ 這是已註冊用戶的 Rich Menu")
                try:
                    rm_detail = rich_menu_service.get_rich_menu(rm_id)
                    if rm_detail:
                        areas = rm_detail.get('areas', [])
                        print(f"      區域數量: {len(areas)}")
                        for j, area in enumerate(areas, 1):
                            action = area.get('action', {})
                            action_data = action.get('data', 'N/A')
                            action_label = action.get('label', 'N/A')
                            print(f"        區域 {j}: {action_label} -> {action_data}")
                except Exception as e:
                    print(f"      ⚠️  取得詳細資訊失敗: {e}")
    except Exception as e:
        print(f"   ❌ 取得 Rich Menu 列表失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 驗證已註冊用戶的 Rich Menu ID
    print("\n📋 步驟 4: 驗證已註冊用戶的 Rich Menu")
    target_rich_menu_id = REGISTERED_USER_RICH_MENU_ID
    
    # 如果環境變數未設定，嘗試查找
    if not target_rich_menu_id:
        print("   環境變數未設定，嘗試自動查找...")
        for rm in rich_menus:
            rm_id = rm.get('richMenuId')
            rm_name = rm.get('name', '')
            
            if rm_name == '已註冊用戶 Rich Menu':
                target_rich_menu_id = rm_id
                print(f"   ✅ 透過 name 欄位找到: {target_rich_menu_id}")
                break
        
        # 如果還是沒找到，透過詳細資訊查找
        if not target_rich_menu_id:
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
                                target_rich_menu_id = rm_id
                                print(f"   ✅ 透過詳細資訊找到: {target_rich_menu_id}")
                                break
                except Exception as e:
                    continue
    
    if target_rich_menu_id:
        print(f"   ✅ 目標 Rich Menu ID: {target_rich_menu_id}")
        
        # 驗證 Rich Menu 是否存在
        try:
            rm_detail = rich_menu_service.get_rich_menu(target_rich_menu_id)
            if rm_detail:
                print(f"   ✅ Rich Menu 存在且有效")
            else:
                print(f"   ❌ Rich Menu 不存在或無效")
                return False
        except Exception as e:
            print(f"   ❌ 驗證 Rich Menu 時發生錯誤: {e}")
            return False
    else:
        print("   ❌ 未找到已註冊用戶的 Rich Menu")
        print("   請確認:")
        print("     1. 已執行 scripts/setup_rich_menus.py 建立 Rich Menu")
        print("     2. 在 .env 檔案中設定 REGISTERED_USER_RICH_MENU_ID")
        return False
    
    # 5. 驗證未註冊用戶的 Rich Menu ID
    print("\n📋 步驟 5: 驗證未註冊用戶的 Rich Menu")
    unregistered_rich_menu_id = UNREGISTERED_USER_RICH_MENU_ID
    
    if not unregistered_rich_menu_id:
        print("   環境變數未設定，嘗試自動查找...")
        for rm in rich_menus:
            rm_id = rm.get('richMenuId')
            rm_name = rm.get('name', '')
            
            if rm_name == '未註冊用戶 Rich Menu':
                unregistered_rich_menu_id = rm_id
                print(f"   ✅ 透過 name 欄位找到: {unregistered_rich_menu_id}")
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
                                print(f"   ✅ 透過詳細資訊找到: {unregistered_rich_menu_id}")
                                break
                except Exception as e:
                    continue
    
    if unregistered_rich_menu_id:
        print(f"   ✅ 目標 Rich Menu ID: {unregistered_rich_menu_id}")
        
        # 驗證 Rich Menu 是否存在
        try:
            rm_detail = rich_menu_service.get_rich_menu(unregistered_rich_menu_id)
            if rm_detail:
                print(f"   ✅ Rich Menu 存在且有效")
            else:
                print(f"   ❌ Rich Menu 不存在或無效")
        except Exception as e:
            print(f"   ❌ 驗證 Rich Menu 時發生錯誤: {e}")
    else:
        print("   ⚠️  未找到未註冊用戶的 Rich Menu")
    
    # 6. 測試設定功能（需要提供測試用的 user_id）
    print("\n📋 步驟 6: 測試設定功能")
    print("   提示: 要測試實際設定功能，請提供一個 LINE User ID")
    print("   例如: python3 scripts/test_rich_menu_setup.py <LINE_USER_ID>")
    print("   或者: python3 scripts/test_rich_menu_setup.py <LINE_USER_ID> registered")
    print("   或者: python3 scripts/test_rich_menu_setup.py <LINE_USER_ID> unregistered")
    
    if len(sys.argv) > 1:
        test_user_id = sys.argv[1]
        test_type = sys.argv[2] if len(sys.argv) > 2 else "registered"
        
        if test_type == "unregistered" and unregistered_rich_menu_id:
            test_rich_menu_id = unregistered_rich_menu_id
            test_type_name = "未註冊用戶"
        elif test_type == "registered" and target_rich_menu_id:
            test_rich_menu_id = target_rich_menu_id
            test_type_name = "已註冊用戶"
        else:
            test_rich_menu_id = target_rich_menu_id
            test_type_name = "已註冊用戶"
        
        if test_rich_menu_id:
            print(f"\n   測試為用戶 {test_user_id} 設定{test_type_name}的 Rich Menu...")
            try:
                success = rich_menu_service.set_user_rich_menu(test_user_id, test_rich_menu_id)
                if success:
                    print(f"   ✅ 成功為用戶 {test_user_id} 設定{test_type_name}的 Rich Menu")
                else:
                    print(f"   ❌ 為用戶 {test_user_id} 設定{test_type_name}的 Rich Menu 失敗")
            except Exception as e:
                print(f"   ❌ 設定時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"   ❌ 無法測試：找不到對應的 Rich Menu ID")
    
    print("\n" + "=" * 60)
    print("✅ 診斷完成")
    print("=" * 60)
    print("\n💡 提示:")
    print("   1. 確認 .env 檔案中的 REGISTERED_USER_RICH_MENU_ID 已正確設定")
    print("   2. 確認 LINE_CHANNEL_ACCESS_TOKEN 有效")
    print("   3. 查看應用程式日誌以獲取更詳細的錯誤資訊")
    print("   4. 如果問題持續，請檢查 LINE 官方帳號的設定")
    print()
    
    return True

if __name__ == "__main__":
    success = test_rich_menu_setup()
    sys.exit(0 if success else 1)
