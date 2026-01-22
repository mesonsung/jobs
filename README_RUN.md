# 執行說明

## ⚠️ 重要：必須從專案根目錄執行

**不要進入 `app/` 目錄內執行！**

## 執行方式

### 方式 1：使用根目錄的 main.py（推薦）

**確保在專案根目錄：**
```bash
cd /home/meson/WorkSpace/Meson/jobs
python3 main.py
```

**檢查當前目錄：**
```bash
pwd
# 應該顯示：/home/meson/WorkSpace/Meson/jobs
# 不應該是：/home/meson/WorkSpace/Meson/jobs/app
```

### 方式 2：使用 Python 模組方式

從專案根目錄執行：

```bash
python -m app.main
```

或

```bash
python3 -m app.main
```

### 方式 3：使用原始檔案（向後兼容）

```bash
python part_time_jobs.py
```

## 注意事項

1. **必須從專案根目錄執行**，不要進入 `app/` 目錄內執行
2. 確保已安裝所有依賴：
   ```bash
   pip install -r requirements.txt
   ```
3. 確保資料庫已啟動（如果使用 PostgreSQL）

## Docker 部署

使用 Docker Compose：

```bash
docker-compose up
```

Dockerfile 已配置為使用新的模組結構：
```dockerfile
CMD ["python", "-m", "app.main"]
```

## 常見錯誤

### 錯誤：ModuleNotFoundError: No module named 'uvicorn'

**解決方法：**
```bash
pip install uvicorn[standard]
```

或安裝所有依賴：
```bash
pip install -r requirements.txt
```

### 錯誤：找不到 app 模組

**原因：** 在錯誤的目錄執行

**解決方法：** 確保從專案根目錄執行，而不是在 `app/` 目錄內

### 錯誤：資料庫連接失敗

**原因：** PostgreSQL 未啟動或配置錯誤

**解決方法：**
1. 啟動 PostgreSQL 服務
2. 檢查 `.env` 或環境變數配置
3. 或使用 Docker Compose 自動啟動資料庫
