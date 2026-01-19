# 兼職工作報名系統

使用 FastAPI 作為後台管理 API，LINE Bot 作為前台報名介面的兼職工作報名系統。

## 功能特色

### 後台功能（FastAPI）
1. **發佈工作** - 透過 API 發佈新的兼職工作
2. **查詢報名清單** - 取得特定工作的所有報名記錄

### 前台功能（LINE Bot）
1. **查看工作列表** - 顯示所有可報名的工作
2. **工作詳情** - 查看工作詳細資訊
3. **報名功能** - 選擇班別並完成報名
4. **取消報名** - 取消已報名的工作

## 安裝與設定

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 2. 設定 LINE Channel Access Token

在 `part_time_jobs.py` 檔案中，確認 `CHANNEL_ACCESS_TOKEN` 已設定為您的 LINE Channel Access Token。

### 3. 設定 LINE Webhook

在 LINE Developers Console 中設定 Webhook URL：
- URL: `https://your-domain.com/webhook`
- 或使用 ngrok 等工具進行本地測試：`https://your-ngrok-url.ngrok.io/webhook`

## 執行系統

### 啟動伺服器

```bash
python part_time_jobs.py
```

系統會同時啟動：
- **FastAPI 後台 API**：`http://localhost:8000`
  - API 文件：`http://localhost:8000/docs`
  - 互動式 API 測試：`http://localhost:8000/redoc`
- **LINE Bot Webhook**：`http://localhost:3000/webhook`

### 分別啟動（可選）

如果需要分別啟動，可以修改程式碼：

```python
# 只啟動 FastAPI
uvicorn api_app:app --host 0.0.0.0 --port 8000

# 只啟動 LINE Bot（需要另外的檔案）
```

## API 使用說明

### 1. 發佈工作

**POST** `/api/jobs`

```json
{
  "name": "餐廳服務員",
  "location": "台北市信義區",
  "date": "2026-01-10",
  "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
  "location_image_url": "https://example.com/image.jpg"
}
```

**回應：**
```json
{
  "id": "JOB_20260110120000_abc12345",
  "name": "餐廳服務員",
  "location": "台北市信義區",
  "date": "2026-01-10",
  "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
  "location_image_url": "https://example.com/image.jpg"
}
```

### 2. 取得所有工作

**GET** `/api/jobs`

### 3. 取得特定工作

**GET** `/api/jobs/{job_id}`

### 4. 取得工作報名清單

**GET** `/api/jobs/{job_id}/applications`

**回應：**
```json
[
  {
    "id": "APP_20260110120000_xyz67890",
    "job_id": "JOB_20260110120000_abc12345",
    "user_id": "U1234567890abcdef",
    "user_name": null,
    "shift": "早班:08-19",
    "applied_at": "2026-01-10 12:00:00"
  }
]
```

## LINE Bot 使用說明

### 指令

- **選單** / **menu** / **工作** / **jobs** - 顯示主選單
- **工作列表** / **查看工作** / **list** - 顯示可報名的工作列表

### 操作流程

#### 報名流程
1. 點擊「查看工作列表」
2. 選擇想要的工作
3. 點擊「報名」按鈕
4. 選擇要報名的班別
5. 顯示報名成功訊息

#### 取消報名流程
1. 在工作詳情頁面點擊「取消報名」
2. 查看報名資訊
3. 點擊「確認取消」
4. 顯示取消成功訊息

## 資料結構

### Job（工作）
- `id`: 工作ID（自動產生）
- `name`: 工作名稱
- `location`: 工作地點
- `date`: 工作日期（格式：YYYY-MM-DD）
- `shifts`: 班別列表
- `location_image_url`: 工作地點圖片 URL（可選）

### Application（報名記錄）
- `id`: 報名ID（自動產生）
- `job_id`: 工作ID
- `user_id`: 使用者ID（LINE User ID）
- `user_name`: 使用者名稱（可選）
- `shift`: 選擇的班別
- `applied_at`: 報名時間

## 注意事項

1. **資料儲存**：目前使用記憶體儲存，重啟後資料會消失。實際應用中應使用資料庫（如 PostgreSQL、MongoDB 等）。

2. **安全性**：
   - 生產環境應使用環境變數儲存 Channel Access Token
   - 建議加入 API 認證機制
   - 使用 HTTPS 保護 Webhook

3. **圖片限制**：
   - LINE 圖片 URL 必須是公開可訪問的 HTTPS URL
   - 建議使用圖片 CDN 服務

4. **班別數量**：
   - LINE 按鈕範本最多支援 4 個按鈕
   - 如果班別超過 4 個，系統會只顯示前 4 個

## 開發建議

### 擴充功能
- 加入資料庫持久化
- 加入使用者認證
- 加入報名通知功能
- 加入工作管理後台介面
- 加入報名統計功能

### 改進建議
- 使用依賴注入管理服務
- 加入錯誤處理和日誌記錄
- 加入單元測試
- 使用環境變數管理設定

## 授權

本專案僅供學習和開發使用。
