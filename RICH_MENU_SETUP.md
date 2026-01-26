# Rich Menu 設定說明

## 快速設定

使用提供的腳本可以一鍵建立並上傳 Rich Menu 到 LINE 官方帳號：

```bash
python3 scripts/setup_rich_menus.py
```

此腳本會：
1. ✅ 建立已註冊用戶的 Rich Menu
2. ✅ 建立未註冊用戶的 Rich Menu
3. ✅ 上傳對應的圖片
4. ✅ 設定未註冊用戶的 Rich Menu 為預設

## 執行結果

執行成功後，您會看到類似以下的輸出：

```
============================================================
✅ Rich Menu 建立完成！
============================================================

📋 Rich Menu ID:
   已註冊用戶: richmenu-xxxxxxxxxxxxx
   未註冊用戶: richmenu-yyyyyyyyyyyyy (預設)
```

## 使用方式

### 1. 自動為註冊用戶設定 Rich Menu

當用戶完成註冊後，系統可以自動為該用戶設定已註冊用戶的 Rich Menu。您可以在註冊完成的處理邏輯中添加：

```python
from app.services.rich_menu_service import LineRichMenuService

# 在註冊完成後
rich_menu_service = LineRichMenuService()
registered_rich_menu_id = "richmenu-xxxxxxxxxxxxx"  # 從設定結果取得
rich_menu_service.set_user_rich_menu(user_id, registered_rich_menu_id)
```

### 2. 透過 API 手動設定

使用後台 API 為特定用戶設定 Rich Menu：

```bash
# 登入取得 token
TOKEN=$(curl -X POST "http://localhost:8880/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# 為用戶設定已註冊用戶的 Rich Menu
curl -X POST "http://localhost:8880/api/rich-menu/set-user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rich_menu_id": "richmenu-xxxxxxxxxxxxx",
    "user_id": "U23c6707574a5f0cbee7118312bb44595"
  }'
```

### 3. 查看所有 Rich Menu

```bash
curl -X GET "http://localhost:8880/api/rich-menu/list" \
  -H "Authorization: Bearer $TOKEN"
```

## Rich Menu 結構

### 已註冊用戶 Rich Menu
- **Rich Menu ID**: `richmenu-xxxxxxxxxxxxx`
- **功能區域**:
  1. 檢視註冊資料 → `action=view_profile&step=view`
  2. 可報班工作 → `action=job&step=list`
  3. 已報班記錄 → `action=job&step=my_applications`

### 未註冊用戶 Rich Menu（預設）
- **Rich Menu ID**: `richmenu-yyyyyyyyyyyyy`
- **功能區域**:
  1. 註冊功能 → `action=register&step=register`
  2. 可報班工作 → `action=job&step=list`

## 注意事項

1. **預設 Rich Menu**: 未註冊用戶的 Rich Menu 已設定為預設，所有新用戶都會看到
2. **用戶專屬 Rich Menu**: 當為用戶設定專屬 Rich Menu 後，該用戶會看到專屬的 Rich Menu，而不是預設的
3. **刪除用戶 Rich Menu**: 可以使用 `DELETE /api/rich-menu/user/{user_id}` 來刪除用戶的專屬 Rich Menu，恢復為預設

## 重新生成圖片

如果需要重新生成範例圖片：

```bash
python3 scripts/generate_rich_menu_samples.py
```

## 重新建立 Rich Menu

如果需要重新建立 Rich Menu（例如修改了功能區域），可以：

1. 先刪除舊的 Rich Menu（可選）
2. 重新執行設定腳本

```bash
# 刪除舊的 Rich Menu（可選）
curl -X DELETE "http://localhost:8880/api/rich-menu/{rich_menu_id}" \
  -H "Authorization: Bearer $TOKEN"

# 重新建立
python3 scripts/setup_rich_menus.py
```
