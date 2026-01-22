# 兼職工作報名系統

使用 FastAPI 作為後台管理 API，LINE Bot 作為前台報名介面的兼職工作報名系統。

## 功能特色

### 後台功能（FastAPI）
1. **發佈工作** - 透過 API 發佈新的兼職工作
2. **查詢工作** - 取得所有工作或特定工作資訊
3. **查詢報名清單** - 取得特定工作的所有報名記錄
4. **查詢所有報名** - 取得系統中所有報名記錄

### 前台功能（LINE Bot）
1. **查看工作列表** - 顯示所有可報名的工作（日期大於等於今天）
2. **工作詳情** - 查看工作詳細資訊（包含地點圖片）
3. **報名功能** - 選擇班別並完成報名
4. **取消報名** - 取消已報名的工作（含確認流程）
5. **查詢已報名** - 查看自己的所有報名記錄

## 系統架構

### 核心模組
1. **JobService** - 工作管理服務
   - 建立、查詢工作
   - 自動產生工作編號（格式：JOB001, JOB002, ...）
   - 過濾可報名工作（日期篩選）

2. **ApplicationService** - 報名管理服務
   - 建立、查詢、取消報名
   - 自動產生報名編號（格式：工作編號_日期_流水號，例如：JOB001_20260110_001）
   - 支援使用者報名索引和工作報名索引

3. **LineMessageService** - LINE 訊息發送服務
   - 發送文字訊息
   - 發送 Flex 訊息
   - 發送按鈕範本
   - 批次發送多個訊息

4. **JobHandler** - 工作事件處理器
   - 處理所有 LINE Bot 互動邏輯
   - 工作列表顯示
   - 報名流程處理
   - 取消報名流程處理

5. **FastAPI 路由** - 後台管理 API
   - RESTful API 設計
   - 自動產生 API 文件

6. **PartTimeJobBot** - 主應用程式
   - 整合所有服務
   - 處理 LINE Webhook
   - 管理伺服器啟動

## 安裝與設定

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

或使用 Python 3：

```bash
python3 -m pip install -r requirements.txt
```

### 2. 設定 LINE Channel Access Token 和 Channel Secret

#### 方法一：直接設定（僅用於開發測試）

在 `part_time_jobs.py` 檔案中，確認 `CHANNEL_ACCESS_TOKEN` 已設定為您的 LINE Channel Access Token。

```python
CHANNEL_ACCESS_TOKEN = "your_channel_access_token_here"
```

#### 方法二：使用環境變數（推薦，用於生產環境）

**設定 Channel Access Token：**
```bash
export LINE_CHANNEL_ACCESS_TOKEN="your_channel_access_token_here"
```

**設定 Channel Secret（用於 Webhook 簽名驗證）：**
```bash
export LINE_CHANNEL_SECRET="your_channel_secret_here"
```

**注意**：
- Channel Access Token 和 Channel Secret 都可以在 LINE Developers Console 中找到
- Channel Secret 用於驗證 Webhook 請求是否真的來自 LINE 平台
- 如果未設定 Channel Secret，系統會跳過簽名驗證（僅用於開發測試）
- **生產環境強烈建議設定 Channel Secret 以確保安全性**

### 3. 設定 LINE Webhook

在 LINE Developers Console 中設定 Webhook URL：
- URL: `https://your-domain.com/`
- 或使用 ngrok 等工具進行本地測試：`https://your-ngrok-url.ngrok.io/`

**注意**：Webhook 路徑為根路徑 `/`，不是 `/webhook`

## 執行系統

### 啟動伺服器

```bash
python3 part_time_jobs.py
```

系統會同時啟動：
- **FastAPI 後台 API**：`http://0.0.0.0:8880`
  - API 文件：`http://localhost:8880/docs`
  - 互動式 API 測試：`http://localhost:8880/redoc`
- **LINE Bot Webhook**：`http://127.0.0.1:3000/`

### 系統特性

- **自動建立測試資料**：首次啟動時會自動建立 3 個測試工作
- **Port 衝突處理**：自動檢測 port 是否已被佔用，避免重複啟動錯誤
- **Flask Debug 模式支援**：支援 Flask reloader，避免重複啟動 FastAPI

### 使用 ngrok 進行本地測試

```bash
# 安裝 ngrok（如果尚未安裝）
# 啟動 ngrok
ngrok http 3000

# 在 LINE Developers Console 設定 Webhook URL
# 例如：https://abc123.ngrok.io/
```

## API 使用說明

### 1. 發佈工作

**POST** `/api/jobs`

**請求範例：**
```json
{
  "name": "餐廳服務員",
  "location": "台北市信義區信義路五段7號",
  "date": "2026-01-10",
  "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
  "location_image_url": "https://example.com/image.jpg"
}
```

**回應範例：**
```json
{
  "id": "JOB001",
  "name": "餐廳服務員",
  "location": "台北市信義區信義路五段7號",
  "date": "2026-01-10",
  "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
  "location_image_url": "https://example.com/image.jpg"
}
```

### 2. 取得所有工作

**GET** `/api/jobs`

**回應：** 返回所有工作列表

### 3. 取得特定工作

**GET** `/api/jobs/{job_id}`

**參數：**
- `job_id`: 工作ID（例如：JOB001）

**回應：** 返回工作詳細資訊

### 4. 取得工作報名清單

**GET** `/api/jobs/{job_id}/applications`

**參數：**
- `job_id`: 工作ID（例如：JOB001）

**回應範例：**
```json
[
  {
    "id": "JOB001_20260110_001",
    "job_id": "JOB001",
    "user_id": "U1234567890abcdef",
    "user_name": null,
    "shift": "早班:08-19",
    "applied_at": "2026-01-10 12:00:00"
  }
]
```

### 5. 取得所有報名記錄

**GET** `/api/applications`

**回應：** 返回系統中所有報名記錄

## LINE Bot 使用說明

### 文字指令

- **選單** / **menu** / **Menu** / **MENU** / **工作** / **jobs** - 顯示主選單
- **工作列表** / **查看工作** / **list** - 顯示可報名的工作列表
- **已報名** / **我的報名** / **報名記錄** / **my_applications** - 查看自己的報名記錄
- 其他任意文字 - 顯示主選單

### 操作流程

#### 報名流程
1. 發送「工作列表」或點擊主選單的「查看工作列表」
2. 系統顯示所有可報名的工作（卡片式顯示，包含工作狀態）
3. 點擊「查看詳情」查看工作詳細資訊（包含地點圖片）
4. 點擊「報名」按鈕
5. 選擇要報名的班別（最多顯示 4 個班別）
6. 系統顯示報名成功訊息，包含報名編號

#### 取消報名流程
1. 在工作詳情頁面或工作列表中點擊「取消報名」
2. 系統顯示報名資訊和確認按鈕
3. 點擊「確認取消」
4. 系統顯示取消成功訊息

#### 查詢已報名
1. 發送「已報名」或點擊主選單的「查詢已報名」
2. 系統顯示所有報名記錄（按時間倒序）
3. 可以點擊「查看詳情」或「取消報名」

## 資料結構

### Job（工作）
- `id`: 工作ID（自動產生，格式：JOB001, JOB002, ...）
- `name`: 工作名稱
- `location`: 工作地點
- `date`: 工作日期（格式：YYYY-MM-DD）
- `shifts`: 班別列表（例如：["早班:08-19", "中班:14-23"]）
- `location_image_url`: 工作地點圖片 URL（可選，必須是 HTTPS）

### Application（報名記錄）
- `id`: 報名ID（自動產生，格式：工作編號_日期_流水號，例如：JOB001_20260110_001）
- `job_id`: 工作ID
- `user_id`: 使用者ID（LINE User ID）
- `user_name`: 使用者名稱（可選，目前未使用）
- `shift`: 選擇的班別
- `applied_at`: 報名時間（格式：YYYY-MM-DD HH:MM:SS）

## 系統限制與注意事項

### 資料儲存
- **目前使用記憶體儲存**：重啟後資料會消失
- **實際應用建議**：使用資料庫（如 PostgreSQL、MongoDB 等）進行持久化

### 安全性
- **生產環境建議**：
  - 使用環境變數儲存 Channel Access Token 和 Channel Secret
  - **啟用 Webhook 簽名驗證**：設定 `LINE_CHANNEL_SECRET` 環境變數
  - 加入 API 認證機制（如 JWT、API Key）
  - 使用 HTTPS 保護 Webhook
  - 驗證 Webhook 請求來源（已實作，需設定 Channel Secret）

**Webhook 簽名驗證說明**：
- 系統已實作 LINE Webhook 簽名驗證功能
- 使用 HMAC-SHA256 演算法驗證請求是否來自 LINE 平台
- 如果驗證失敗，會返回 403 Forbidden
- 設定 `LINE_CHANNEL_SECRET` 環境變數即可啟用驗證

### LINE API 限制
- **圖片 URL**：
  - 必須是公開可訪問的 HTTPS URL
  - 建議使用圖片 CDN 服務
  - 支援 JPEG、PNG 格式

- **按鈕數量**：
  - LINE 按鈕範本最多支援 4 個按鈕
  - 如果班別超過 4 個，系統會只顯示前 4 個

- **訊息長度**：
  - 按鈕範本文字最多 60 字元
  - 系統會自動截斷過長文字

### 工作編號規則
- 格式：`JOB` + 3 位數流水號（例如：JOB001, JOB002, ...）
- 自動遞增，重啟後會從現有最大編號繼續

### 報名編號規則
- 格式：`工作編號_日期_流水號`（例如：JOB001_20260110_001）
- 日期格式：YYYYMMDD
- 流水號：3 位數，按當天報名順序遞增

## 開發建議

### 擴充功能
- [ ] 加入資料庫持久化（PostgreSQL、MongoDB 等）
- [ ] 加入使用者認證和權限管理
- [ ] 加入報名通知功能（Email、簡訊等）
- [ ] 加入工作管理後台介面（Web UI）
- [ ] 加入報名統計和分析功能
- [ ] 加入報名名額限制
- [ ] 加入報名截止時間
- [ ] 加入工作分類和搜尋功能

### 改進建議
- [ ] 使用依賴注入管理服務（如 FastAPI Depends）
- [ ] 加入完整的錯誤處理和日誌記錄
- [ ] 加入單元測試和整合測試
- [ ] 使用環境變數管理所有設定
- [ ] 加入 API 版本控制
- [ ] 加入請求速率限制
- [ ] 加入資料驗證和清理
- [ ] 優化訊息發送效能（批次處理）

## 故障排除

### Port 已被佔用
如果看到 "address already in use" 錯誤：
- 檢查是否有其他程序正在使用 port 8880 或 3000
- 使用 `lsof -i :8880` 或 `lsof -i :3000` 查看佔用情況
- 終止佔用 port 的程序或修改程式碼中的 port 設定

### Flask Debug 模式重複啟動
系統已處理此問題，會自動檢測主進程並只在主進程中啟動 FastAPI。

### LINE Webhook 無法接收訊息
- 確認 Webhook URL 設定正確
- 確認 Channel Access Token 正確
- 檢查防火牆設定
- 使用 ngrok 時確認 URL 已更新到 LINE Developers Console

### Webhook 簽名驗證失敗（403 Forbidden）
- 確認已設定 `LINE_CHANNEL_SECRET` 環境變數
- 確認 Channel Secret 值正確（從 LINE Developers Console 取得）
- 檢查系統時間是否正確（簽名驗證依賴時間戳記）
- 開發測試時可以暫時不設定 Channel Secret（系統會跳過驗證並顯示警告）

## 授權

本專案僅供學習和開發使用。
