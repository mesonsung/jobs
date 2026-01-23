# Good Job 報班系統

使用 FastAPI 作為後台管理 API，LINE Bot 作為前台報班介面的 Good Job 報班系統。

---

## 目錄

- [功能特色](#功能特色)
- [系統架構](#系統架構)
- [快速開始](#快速開始)
- [Docker 部署](#docker-部署)
- [API 文件](#api-文件)
- [LINE Bot 使用說明](#line-bot-使用說明)
- [資料結構](#資料結構)
- [系統限制與注意事項](#系統限制與注意事項)
- [開發建議](#開發建議)
- [故障排除](#故障排除)
- [授權](#授權)

---

## 功能特色

### 後台功能（FastAPI）

1. **使用者認證** - JWT 認證機制，支援登入和註冊報班帳號
2. **權限管理** - 區分管理員和一般使用者權限
3. **發佈工作** - 透過 API 發佈新的 Good Job（需要管理員權限）
4. **查詢工作** - 取得所有工作或特定工作資訊（需要認證）
5. **查詢報班清單** - 取得特定工作的所有報班記錄（需要管理員權限）
6. **查詢所有報班** - 取得系統中所有報班記錄（需要管理員權限）
7. **使用者管理** - 管理使用者帳號（需要管理員權限）
8. **地理編碼** - 根據地址取得座標，或根據座標取得地址

### 前台功能（LINE Bot）

1. **LINE 使用者註冊報班帳號** - 透過 LINE 進行註冊報班帳號（不需要密碼）
2. **查看工作列表** - 顯示所有可報班的工作（日期大於等於今天）
3. **工作詳情** - 查看工作詳細資訊（包含地點圖片）
4. **報班功能** - 選擇班別並完成報班（僅限已註冊報班帳號使用者）
5. **取消報班** - 取消已報班的工作（含確認流程）
6. **查詢已報班** - 查看自己的所有報班記錄

---

## 系統架構

### 核心模組

#### 1. JobService - 工作管理服務
- 建立、查詢工作
- 自動產生工作編號（格式：JOB001, JOB002, ...）
- 過濾可報班工作（日期篩選）

#### 2. ApplicationService - 報班管理服務
- 建立、查詢、取消報班
- 自動產生報班編號（格式：工作編號-日期-流水號，例如：JOB001-20260110-001）
- 支援使用者報班索引和工作報班索引

#### 3. AuthService - 認證和權限管理服務
- 使用者註冊報班帳號和登入
- JWT Token 產生和驗證
- 密碼加密（使用 bcrypt）
- 權限檢查（管理員/一般使用者）
- 預設管理員帳號建立

#### 4. LineMessageService - LINE 訊息發送服務
- 發送文字訊息
- 發送 Flex 訊息
- 發送按鈕範本
- 批次發送多個訊息

#### 5. JobHandler - 工作事件處理器
- 處理所有 LINE Bot 互動邏輯
- 工作列表顯示
- 報班流程處理
- 取消報班流程處理

#### 6. FastAPI 路由 - 後台管理 API
- RESTful API 設計
- JWT 認證保護
- 權限管理
- 自動產生 API 文件

#### 7. PartTimeJobBot - 主應用程式
- 整合所有服務
- 處理 LINE Webhook
- 管理伺服器啟動

---

## 快速開始

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

或使用 Python 3：

```bash
python3 -m pip install -r requirements.txt
```

### 2. 環境變數設定

#### 必要環境變數

**LINE Bot 設定：**
```bash
export LINE_CHANNEL_ACCESS_TOKEN="your_channel_access_token_here"
export LINE_CHANNEL_SECRET="your_channel_secret_here"
```

**JWT 設定：**
```bash
export JWT_SECRET_KEY="your-secret-key-here"
```

**Google Maps API Key（用於地理編碼）：**
```bash
export GOOGLE_MAPS_API_KEY="your-google-maps-api-key-here"
```

#### 可選環境變數

**預設管理員帳號：**
```bash
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="admin123"
```

#### 取得 API 金鑰

**LINE Channel Access Token 和 Channel Secret：**
1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 建立或選擇現有的 Provider 和 Channel
3. 在 Channel 設定頁面取得 Channel Access Token 和 Channel Secret

**Google Maps API Key：**
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 啟用「Geocoding API」
4. 建立 API 金鑰
5. 將 API 金鑰設定為環境變數 `GOOGLE_MAPS_API_KEY`

**注意事項：**
- Channel Access Token 和 Channel Secret 都可以在 LINE Developers Console 中找到
- Channel Secret 用於驗證 Webhook 請求是否真的來自 LINE 平台
- 如果未設定 Channel Secret，系統會跳過簽名驗證（僅用於開發測試）
- **生產環境強烈建議設定 Channel Secret 以確保安全性**
- **JWT Secret Key 必須在生產環境中設定，且應使用強隨機字串**
- Google Maps API 有使用限制，請參考 [Google Maps Platform 定價](https://developers.google.com/maps/billing-and-pricing/pricing)
- 建議設定 API 金鑰的使用限制以確保安全性
- 預設管理員帳號密碼應在生產環境中修改

### 3. 設定 LINE Webhook

在 LINE Developers Console 中設定 Webhook URL：
- **URL**: `https://your-domain.com/`
- **本地測試**: 使用 ngrok 等工具：`https://your-ngrok-url.ngrok.io/`

**注意：** Webhook 路徑為根路徑 `/`，不是 `/webhook`

### 4. 啟動伺服器

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

---

## Docker 部署

### 使用 Docker Compose（推薦）

#### 1. 複製環境變數範例檔案

```bash
cp .env.example .env
```

#### 2. 編輯 `.env` 檔案

填入以下設定：

```bash
# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here

# JWT 設定（生產環境必須修改）
JWT_SECRET_KEY=your-secret-key-change-this-in-production

# Google Maps API Key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# 管理員帳號設定（可選）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# PostgreSQL 資料庫設定
POSTGRES_USER=goodjob
POSTGRES_PASSWORD=goodjob123
POSTGRES_DB=goodjob_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://goodjob:goodjob123@postgres:5432/goodjob_db
```

**注意：** `docker-compose.yml` 已配置為自動從 `.env` 檔案讀取環境變數（透過 `env_file: - .env`），您只需要編輯 `.env` 檔案即可。

#### 3. 啟動服務

```bash
docker-compose up -d
```

#### 4. 查看日誌

```bash
docker-compose logs -f
```

#### 5. 停止服務

```bash
docker-compose down
```

### 使用 Docker 直接運行

#### 1. 建立映像

```bash
docker build -t good-job-bot .
```

#### 2. 運行容器

```bash
docker run -d \
  --name good-job-bot \
  -p 3000:3000 \
  -p 8880:8880 \
  -e LINE_CHANNEL_ACCESS_TOKEN="your_token_here" \
  -e LINE_CHANNEL_SECRET="your_secret_here" \
  -e JWT_SECRET_KEY="your-secret-key-here" \
  -e GOOGLE_MAPS_API_KEY="your_api_key_here" \
  --restart unless-stopped \
  good-job-bot
```

#### 3. 查看日誌

```bash
docker logs -f good-job-bot
```

#### 4. 停止容器

```bash
docker stop good-job-bot
docker rm good-job-bot
```

### Docker 部署注意事項

#### 端口映射
- `3000:3000` - LINE Bot (Flask Webhook)
- `8880:8880` - FastAPI API 文件
- `5432:5432` - PostgreSQL 資料庫（可選，僅用於外部連接）

#### 環境變數
- 所有敏感資訊應透過環境變數傳入
- 生產環境請使用 `.env` 檔案或 Docker secrets
- 必須設定的環境變數：`LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`
- PostgreSQL 設定可透過環境變數自訂（預設值已配置）

#### 資料持久化
- **PostgreSQL 資料庫已整合**：使用 Docker volume `postgres_data` 持久化資料
- 資料庫資料會保存在 Docker volume 中，容器重啟後不會遺失
- 如需備份資料，可備份 Docker volume 或使用 `pg_dump`
- 清除資料：執行 `docker-compose down -v`（會刪除所有 volume）
- **如果遇到資料庫不存在錯誤**：可能是 volume 使用了舊的資料庫名稱，執行 `docker-compose down -v` 清除 volume 後重新啟動

#### 健康檢查
- Docker Compose 已包含健康檢查設定
- 檢查 FastAPI 文件頁面是否可訪問
- 使用 Python 內建的 `urllib` 進行檢查（無需額外依賴）

#### 開發模式
- 如需即時反映程式碼變更，可在 `docker-compose.yml` 中取消註解 volume 掛載
- 生產環境建議移除 volume 掛載，使用映像內的程式碼

#### 映像優化
- 使用 **Alpine Linux** 作為基礎映像（極小化映像大小）
- 使用多階段構建（multi-stage build）減少映像大小
- 構建階段包含編譯工具，運行階段僅保留運行時依賴
- 使用非 root 使用者運行應用程式（安全性最佳實踐）
- 自動清理構建緩存和不需要的檔案
- 預期映像大小約為 **100-150MB**（相較於未優化版本減少約 70-80%）
- Alpine 使用 `apk` 套件管理器，映像更小但構建時間可能稍長

---

## API 文件

### 認證相關 API

#### 1. 註冊報班帳號新使用者

**POST** `/api/auth/register`

**請求範例：**
```json
{
  "username": "testuser",
  "password": "password123",
  "email": "test@example.com",
  "full_name": "測試使用者",
  "is_admin": false
}
```

**回應範例：**
```json
{
  "id": "USER-002",
  "username": "testuser",
  "email": "test@example.com",
  "full_name": "測試使用者",
  "is_admin": false,
  "is_active": true,
  "created_at": "2026-01-10 12:00:00"
}
```

#### 2. 使用者登入

**POST** `/api/auth/login`

**請求格式：** `application/x-www-form-urlencoded`

**參數：**
- `username`: 使用者名稱
- `password`: 密碼

**回應範例：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**注意：** 將 `access_token` 用於後續 API 請求的 Authorization header：
```
Authorization: Bearer {access_token}
```

#### 3. 取得當前使用者資訊

**GET** `/api/auth/me`

**認證：** 需要 Bearer Token

**回應：** 返回當前登入使用者的資訊

### 地理編碼 API

#### 4. 根據地址取得座標

**POST** `/api/geocode`

**認證：** 需要認證（Bearer Token）

**請求範例：**
```json
{
  "address": "台北市信義區信義路五段7號"
}
```

**回應範例：**
```json
{
  "address": "台北市信義區信義路五段7號",
  "latitude": 25.0339639,
  "longitude": 121.5644722,
  "success": true,
  "message": "成功取得座標"
}
```

#### 5. 根據座標取得地址（反向地理編碼）

**POST** `/api/geocode/reverse`

**認證：** 需要認證（Bearer Token）

**請求範例：**
```json
{
  "latitude": 25.0339639,
  "longitude": 121.5644722
}
```

**回應範例：**
```json
{
  "latitude": 25.0339639,
  "longitude": 121.5644722,
  "address": "台北市信義區信義路五段7號",
  "success": true,
  "message": "成功取得地址"
}
```

### 工作管理 API

#### 6. 發佈工作

**POST** `/api/jobs`

**認證：** 需要管理員權限（Bearer Token）

**請求範例：**
```json
{
  "name": "餐廳服務員",
  "location": "台北市信義區信義路五段7號",
  "date": "2026-01-10",
  "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
  "location_image_url": "https://example.com/image.jpg",
  "latitude": null,
  "longitude": null
}
```

**注意：**
- `latitude` 和 `longitude` 為可選欄位
- 如果未提供座標，系統會自動使用 Google Maps Geocoding API 從地址取得座標
- 如果已提供座標，系統會直接使用提供的座標

**回應範例：**
```json
{
  "id": "JOB001",
  "name": "餐廳服務員",
  "location": "台北市信義區信義路五段7號",
  "date": "2026-01-10",
  "shifts": ["早班:08-19", "中班:14-23", "晚班:22-07"],
  "location_image_url": "https://example.com/image.jpg",
  "latitude": 25.0339639,
  "longitude": 121.5644722
}
```

#### 7. 取得所有工作

**GET** `/api/jobs`

**認證：** 需要認證（Bearer Token）

**回應：** 返回所有工作列表

#### 8. 取得特定工作

**GET** `/api/jobs/{job_id}`

**認證：** 需要認證（Bearer Token）

**參數：**
- `job_id`: 工作ID（例如：JOB001）

**回應：** 返回工作詳細資訊（包含座標）

#### 9. 取得工作報班清單

**GET** `/api/jobs/{job_id}/applications`

**認證：** 需要管理員權限（Bearer Token）

**參數：**
- `job_id`: 工作ID（例如：JOB001）

**回應範例：**
```json
[
  {
    "id": "JOB001-20260110-001",
    "job_id": "JOB001",
    "user_id": "U1234567890abcdef",
    "user_name": null,
    "shift": "早班:08-19",
    "applied_at": "2026-01-10 12:00:00"
  }
]
```

#### 10. 取得所有報班記錄

**GET** `/api/applications`

**認證：** 需要管理員權限（Bearer Token）

**回應：** 返回系統中所有報班記錄

### 使用者管理 API（管理員專用）

#### 11. 取得所有使用者列表

**GET** `/api/users`

**認證：** 需要管理員權限（Bearer Token）

**回應：** 返回所有使用者列表

#### 12. 取得特定使用者資訊

**GET** `/api/users/{username}`

**認證：** 需要管理員權限（Bearer Token）

**參數：**
- `username`: 使用者名稱

**回應：** 返回使用者詳細資訊

### 認證與權限說明

#### 預設管理員帳號

系統啟動時會自動建立預設管理員帳號：
- **使用者名稱：** `admin`（可透過環境變數 `ADMIN_USERNAME` 修改）
- **密碼：** `admin123`（可透過環境變數 `ADMIN_PASSWORD` 修改）

**⚠️ 重要：** 生產環境請務必修改預設密碼！

#### 權限說明

- **一般使用者：** 可以查看工作列表和工作詳情
- **管理員：** 可以建立工作、查看所有報班記錄、管理使用者

#### Token 使用方式

1. 使用 `/api/auth/login` 端點登入取得 Token
2. 在後續 API 請求的 Header 中加入：
   ```
   Authorization: Bearer {access_token}
   ```
3. Token 有效期為 30 天

---

## LINE Bot 使用說明

### 文字指令

- **選單** / **menu** / **Menu** / **MENU** / **工作** / **jobs** - 顯示主選單
- **註冊報班帳號** / **register** / **Register** / **REGISTER** - 註冊報班帳號為系統使用者
- **工作列表** / **查看工作** / **list** - 顯示可報班的工作列表
- **已報班** / **我的報班** / **報班記錄** / **my_applications** - 查看自己的報班記錄
- 其他任意文字 - 顯示主選單

### 註冊報班帳號說明

- **LINE 使用者註冊報班帳號**：透過 LINE Bot 註冊報班帳號，不需要密碼
- **註冊報班帳號後才能報班**：只有已註冊報班帳號的使用者才能報班工作
- **多步驟註冊報班帳號**：需要填寫姓名、手機、地址、Email（Email 可選）
- **資料驗證**：手機號碼會驗證格式（台灣手機號碼：10位數，09開頭）
- **註銷報班帳號**：在註冊報班帳號過程中輸入「取消」可隨時註銷報班帳號流程
- **使用者名稱**：直接使用 LINE User ID 作為使用者名稱（不另外產生）

### 操作流程

#### 註冊報班帳號流程

1. 發送「註冊報班帳號」或點擊主選單的「📝 註冊報班帳號」按鈕
2. 依序輸入以下資料：
   - **第一步：姓名** - 輸入您的姓名
   - **第二步：手機號碼** - 輸入10位數手機號碼（例如：0912345678）
   - **第三步：地址** - 輸入您的地址
   - **第四步：Email** - 輸入 Email（可選，輸入「跳過」即可略過）
3. 系統顯示註冊報班帳號成功訊息，包含所有註冊報班帳號資訊

#### 報班流程

1. **首次使用請先註冊報班帳號**：發送「註冊報班帳號」完成註冊報班帳號
2. 發送「工作列表」或點擊主選單的「查看工作列表」
3. 系統顯示所有可報班的工作（卡片式顯示，包含工作狀態）
4. 點擊「查看詳情」查看工作詳細資訊（包含地點圖片）
5. 點擊「報班」按鈕（未註冊報班帳號使用者會看到註冊報班帳號提示）
6. 選擇要報班的班別（最多顯示 4 個班別）
7. 系統顯示報班成功訊息，包含報班編號

**注意：** 未註冊報班帳號的使用者無法報班工作，系統會提示先完成註冊報班帳號。

#### 取消報班流程

1. 在工作詳情頁面或工作列表中點擊「取消報班」
2. 系統顯示報班資訊和確認按鈕
3. 點擊「確認取消」
4. 系統顯示取消成功訊息

#### 查詢已報班

1. 發送「已報班」或點擊主選單的「查詢已報班」
2. 系統顯示所有報班記錄（按時間倒序）
3. 可以點擊「查看詳情」或「取消報班」

---

## 資料結構

### Job（工作）

- `id`: 工作ID（自動產生，格式：JOB001, JOB002, ...）
- `name`: 工作名稱
- `location`: 工作地點
- `date`: 工作日期（格式：YYYY-MM-DD）
- `shifts`: 班別列表（例如：["早班:08-19", "中班:14-23"]）
- `location_image_url`: 工作地點圖片 URL（可選，必須是 HTTPS）
- `latitude`: 緯度（可選，自動從地址取得）
- `longitude`: 經度（可選，自動從地址取得）

### Application（報班記錄）

- `id`: 報班ID（自動產生，格式：工作編號-日期-流水號，例如：JOB001-20260110-001）
- `job_id`: 工作ID
- `user_id`: 使用者ID（LINE User ID）
- `user_name`: 使用者名稱（可選，目前未使用）
- `shift`: 選擇的班別
- `applied_at`: 報班時間（格式：YYYY-MM-DD HH:MM:SS）

### 編號規則

#### 工作編號
- 格式：`JOB` + 3 位數流水號（例如：JOB001, JOB002, ...）
- 自動遞增，重啟後會從現有最大編號繼續

#### 報班編號
- 格式：`工作編號-日期-流水號`（例如：JOB001-20260110-001）
- 日期格式：YYYYMMDD
- 流水號：3 位數，按當天報班順序遞增

---

## 系統限制與注意事項

### 資料儲存

- **目前使用記憶體儲存**：重啟後資料會消失
- **實際應用建議**：使用資料庫（如 PostgreSQL、MongoDB 等）進行持久化

### 安全性

**生產環境建議：**
- 使用環境變數儲存 Channel Access Token 和 Channel Secret
- **啟用 Webhook 簽名驗證**：設定 `LINE_CHANNEL_SECRET` 環境變數
- 加入 API 認證機制（如 JWT、API Key）
- 使用 HTTPS 保護 Webhook
- 驗證 Webhook 請求來源（已實作，需設定 Channel Secret）

**Webhook 簽名驗證說明：**
- 系統已實作 LINE Webhook 簽名驗證功能
- 使用 HMAC-SHA256 演算法驗證請求是否來自 LINE 平台
- 如果驗證失敗，會返回 403 Forbidden
- 設定 `LINE_CHANNEL_SECRET` 環境變數即可啟用驗證

### LINE API 限制

#### 圖片 URL
- 必須是公開可訪問的 HTTPS URL
- 建議使用圖片 CDN 服務
- 支援 JPEG、PNG 格式

#### 按鈕數量
- LINE 按鈕範本最多支援 4 個按鈕
- 如果班別超過 4 個，系統會只顯示前 4 個

#### 訊息長度
- 按鈕範本文字最多 60 字元
- 系統會自動截斷過長文字

---

## 開發建議

### 擴充功能

- [x] 加入使用者認證和權限管理
- [x] 加入 Google Maps 座標取得功能
- [x] 加入資料庫持久化（PostgreSQL、MongoDB 等）
- [ ] 加入報班通知功能（Email、簡訊等）
- [ ] 加入工作管理後台介面（Web UI）
- [ ] 加入報班統計和分析功能
- [ ] 加入報班名額限制
- [ ] 加入報班截止時間
- [ ] 加入工作分類和搜尋功能
- [ ] 在地圖上顯示工作地點

### 改進建議

- [ ] 使用依賴注入管理服務（如 FastAPI Depends）
- [ ] 加入完整的錯誤處理和日誌記錄
- [ ] 加入單元測試和整合測試
- [ ] 使用環境變數管理所有設定
- [ ] 加入 API 版本控制
- [ ] 加入請求速率限制
- [ ] 加入資料驗證和清理
- [ ] 優化訊息發送效能（批次處理）

---

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

---

## 授權

本專案僅供學習和開發使用。
