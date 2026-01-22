# 專案重構說明

## 重構目標

將單一檔案 `part_time_jobs.py` 重構為模組化結構，提高代碼可維護性和可擴展性。

## 新的專案結構

```
app/
├── __init__.py                 # 應用程式初始化
├── config.py                   # 配置設定
├── main.py                     # 主入口點（待完成）
├── core/
│   ├── __init__.py
│   ├── database.py            # 資料庫設定 ✅
│   └── security.py            # 認證相關 ✅
├── models/
│   ├── __init__.py
│   ├── job.py                 # Job 相關模型 ✅
│   ├── user.py                # User 相關模型 ✅
│   └── schemas.py             # Pydantic 模型 ✅
├── services/
│   ├── __init__.py
│   ├── job_service.py         # 工作服務 ✅
│   ├── application_service.py # 報班服務 ✅
│   └── geocoding_service.py   # 地理編碼服務 ✅
├── bot/
│   ├── __init__.py
│   ├── handler.py             # JobHandler（待遷移）
│   └── bot.py                 # PartTimeJobBot（待遷移）
└── api/
    ├── __init__.py
    ├── main.py                # FastAPI app（待遷移）
    ├── routes/
    │   ├── __init__.py
    │   ├── auth.py            # 認證路由（待遷移）
    │   ├── jobs.py            # 工作路由（待遷移）
    │   └── users.py           # 使用者路由（待遷移）
    └── dependencies.py        # FastAPI 依賴（待遷移）
```

## 已完成的重構

✅ **配置模組** (`app/config.py`)
- 集中管理所有環境變數和配置

✅ **資料庫核心** (`app/core/database.py`)
- 資料庫連接和會話管理
- Base 類別定義

✅ **安全認證** (`app/core/security.py`)
- 密碼加密和驗證
- JWT Token 處理

✅ **資料模型** (`app/models/`)
- SQLAlchemy 模型（JobModel, ApplicationModel, UserModel）
- Pydantic 模型（用於 API）

✅ **服務層** (`app/services/`)
- JobService - 工作管理
- ApplicationService - 報班管理
- GeocodingService - 地理編碼

## 待完成的重構

⏳ **認證服務** (`app/services/auth_service.py`)
- 需要從 `part_time_jobs.py` 提取 AuthService 類別
- 約 400 行代碼

⏳ **LINE 訊息服務** (`app/services/line_message_service.py`)
- 需要從 `part_time_jobs.py` 提取 LineMessageService 類別
- 約 100 行代碼

⏳ **LINE Bot 處理器** (`app/bot/handler.py`)
- 需要從 `part_time_jobs.py` 提取 JobHandler 類別
- 約 1300 行代碼

⏳ **LINE Bot 主程式** (`app/bot/bot.py`)
- 需要從 `part_time_jobs.py` 提取 PartTimeJobBot 類別
- 約 250 行代碼

⏳ **FastAPI 路由** (`app/api/`)
- 需要從 `part_time_jobs.py` 提取所有 API 路由
- 約 200 行代碼

⏳ **主入口點** (`app/main.py`)
- 整合所有模組
- 初始化服務
- 啟動伺服器

## 遷移步驟

1. **階段 1：基礎結構** ✅
   - 創建目錄結構
   - 遷移配置和核心模組
   - 遷移資料模型

2. **階段 2：服務層** ✅
   - 遷移業務邏輯服務
   - 處理依賴關係

3. **階段 3：認證和 LINE 服務** ⏳
   - 遷移 AuthService
   - 遷移 LineMessageService

4. **階段 4：Bot 處理** ⏳
   - 遷移 JobHandler
   - 遷移 PartTimeJobBot

5. **階段 5：API 路由** ⏳
   - 遷移 FastAPI 路由
   - 設置依賴注入

6. **階段 6：整合和測試** ⏳
   - 創建主入口點
   - 更新 Dockerfile
   - 測試所有功能

## 使用方式

目前系統仍使用 `part_time_jobs.py` 作為主入口點，以保持功能正常。

未來完成所有遷移後，可以切換到新的結構：

```python
# 新的使用方式（待完成）
from app.main import create_app
app = create_app()
app.run()
```

## 注意事項

- 重構過程中保持向後兼容
- 逐步遷移，確保每個階段都能正常運行
- 更新所有導入語句
- 處理循環依賴問題
- 確保測試覆蓋
