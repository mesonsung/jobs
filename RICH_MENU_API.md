# LINE Rich Menu 管理 API 使用說明

## 概述

此 API 用於管理 LINE 官方帳號的 Rich Menu（圖文選單）。系統支援兩種 Rich Menu：

1. **已註冊用戶 Rich Menu**：包含「檢視註冊資料」、「可報班工作」、「已報班記錄」三個功能
2. **未註冊用戶 Rich Menu**：包含「註冊功能」、「可報班工作」兩個功能

## API 端點

所有 API 都需要管理員權限（需要登入並具有管理員身份）。

### 1. 建立已註冊用戶的 Rich Menu

**POST** `/api/rich-menu/create/registered`

建立已註冊用戶的 Rich Menu。

**請求參數：**
- `image_path` (可選, Form): 圖片檔案路徑（本地檔案系統路徑）
- `image_file` (可選, File): 圖片檔案（透過 multipart/form-data 上傳）

**注意：** 圖片必須符合 LINE Rich Menu 的規格：
- 尺寸：2500 x 843 像素
- 格式：JPEG 或 PNG
- 檔案大小：最大 1 MB

**回應範例：**
```json
{
  "success": true,
  "rich_menu_id": "richmenu-xxxxxxxxxxxxx",
  "message": "已註冊用戶 Rich Menu 建立成功"
}
```

### 2. 建立未註冊用戶的 Rich Menu

**POST** `/api/rich-menu/create/unregistered`

建立未註冊用戶的 Rich Menu。

**請求參數：**
- `image_path` (可選, Form): 圖片檔案路徑（本地檔案系統路徑）
- `image_file` (可選, File): 圖片檔案（透過 multipart/form-data 上傳）

**回應範例：**
```json
{
  "success": true,
  "rich_menu_id": "richmenu-yyyyyyyyyyyyy",
  "message": "未註冊用戶 Rich Menu 建立成功"
}
```

### 3. 設定預設 Rich Menu

**POST** `/api/rich-menu/set-default`

設定預設 Rich Menu（所有用戶都會看到此 Rich Menu）。

**請求 Body：**
```json
{
  "rich_menu_id": "richmenu-xxxxxxxxxxxxx"
}
```

**回應範例：**
```json
{
  "success": true,
  "message": "預設 Rich Menu 設定成功"
}
```

### 4. 為特定用戶設定 Rich Menu

**POST** `/api/rich-menu/set-user`

為特定用戶設定 Rich Menu。

**請求 Body：**
```json
{
  "rich_menu_id": "richmenu-xxxxxxxxxxxxx",
  "user_id": "U23c6707574a5f0cbee7118312bb44595"
}
```

**回應範例：**
```json
{
  "success": true,
  "message": "用戶 U23c6707574a5f0cbee7118312bb44595 的 Rich Menu 設定成功"
}
```

### 5. 取得所有 Rich Menu 列表

**GET** `/api/rich-menu/list`

取得所有已建立的 Rich Menu 列表。

**回應範例：**
```json
{
  "success": true,
  "rich_menus": [
    {
      "richMenuId": "richmenu-xxxxxxxxxxxxx",
      "name": "已註冊用戶 Rich Menu",
      "chatBarText": "選單",
      "size": {
        "width": 2500,
        "height": 843
      }
    }
  ],
  "count": 1
}
```

### 6. 取得 Rich Menu 詳細資訊

**GET** `/api/rich-menu/{rich_menu_id}`

取得指定 Rich Menu 的詳細資訊。

**回應範例：**
```json
{
  "success": true,
  "rich_menu": {
    "richMenuId": "richmenu-xxxxxxxxxxxxx",
    "name": "已註冊用戶 Rich Menu",
    "chatBarText": "選單",
    "size": {
      "width": 2500,
      "height": 843
    },
    "areas": [...]
  }
}
```

### 7. 刪除 Rich Menu

**DELETE** `/api/rich-menu/{rich_menu_id}`

刪除指定的 Rich Menu。

**回應範例：**
```json
{
  "success": true,
  "message": "Rich Menu 刪除成功"
}
```

### 8. 刪除用戶的 Rich Menu

**DELETE** `/api/rich-menu/user/{user_id}`

刪除特定用戶的 Rich Menu（恢復為預設或無 Rich Menu）。

**回應範例：**
```json
{
  "success": true,
  "message": "用戶 U23c6707574a5f0cbee7118312bb44595 的 Rich Menu 刪除成功"
}
```

## Rich Menu 結構說明

### 已註冊用戶 Rich Menu

圖片佈局（2500 x 843 像素）：
```
|已註冊用戶|
|檢視註冊資料|可報班工作|已報班記錄|
```

功能區域：
1. **檢視註冊資料** (x: 0-833, y: 0-843)
   - Postback: `action=view_profile&step=view`

2. **可報班工作** (x: 833-1666, y: 0-843)
   - Postback: `action=job&step=list`

3. **已報班記錄** (x: 1666-2500, y: 0-843)
   - Postback: `action=job&step=my_applications`

### 未註冊用戶 Rich Menu

圖片佈局（2500 x 843 像素）：
```
|未註冊用戶|
|註冊功能|可報班工作|
```

功能區域：
1. **註冊功能** (x: 0-1250, y: 0-843)
   - Postback: `action=register&step=register`

2. **可報班工作** (x: 1250-2500, y: 0-843)
   - Postback: `action=job&step=list`

## 使用範例

### 使用 cURL 建立 Rich Menu

```bash
# 建立已註冊用戶的 Rich Menu（使用檔案路徑）
curl -X POST "http://localhost:8880/api/rich-menu/create/registered" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "image_path=/path/to/registered_user_menu.jpg"

# 建立未註冊用戶的 Rich Menu（上傳檔案）
curl -X POST "http://localhost:8880/api/rich-menu/create/unregistered" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "image_file=@unregistered_user_menu.jpg"

# 設定預設 Rich Menu
curl -X POST "http://localhost:8880/api/rich-menu/set-default" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rich_menu_id": "richmenu-xxxxxxxxxxxxx"}'
```

### 使用 Python requests

```python
import requests

# 登入取得 token
login_response = requests.post(
    "http://localhost:8880/api/auth/login",
    data={"username": "admin", "password": "admin123"}
)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 建立已註冊用戶的 Rich Menu
with open("registered_user_menu.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8880/api/rich-menu/create/registered",
        headers=headers,
        files={"image_file": f}
    )
    rich_menu_id = response.json()["rich_menu_id"]

# 設定為預設 Rich Menu
requests.post(
    "http://localhost:8880/api/rich-menu/set-default",
    headers=headers,
    json={"rich_menu_id": rich_menu_id}
)
```

## 注意事項

1. **圖片規格**：
   - 尺寸必須是 2500 x 843 像素
   - 格式：JPEG 或 PNG
   - 檔案大小：最大 1 MB

2. **權限**：所有 API 都需要管理員權限

3. **Rich Menu 限制**：
   - 每個官方帳號最多可以有 1000 個 Rich Menu
   - 每個用戶只能有一個 Rich Menu（可以透過設定用戶專屬的 Rich Menu 來覆蓋預設）

4. **建議流程**：
   1. 先建立兩個 Rich Menu（已註冊和未註冊）
   2. 設定未註冊用戶的 Rich Menu 為預設
   3. 當用戶註冊後，透過 `set-user` API 為該用戶設定已註冊用戶的 Rich Menu
