# 快速開始指南

## 執行應用程式

### ✅ 正確的執行方式

```bash
# 1. 進入專案根目錄
cd /home/meson/WorkSpace/Meson/jobs

# 2. 確認當前目錄（應該看到 main.py 和 app/ 目錄）
ls -la | grep -E "main.py|app/"

# 3. 執行應用程式
python3 main.py
```

### ❌ 錯誤的執行方式

**不要在 app/ 目錄內執行：**
```bash
cd app/          # ❌ 錯誤！
python3 main.py # ❌ 會找不到模組
```

## 如果遇到 "ModuleNotFoundError: No module named 'uvicorn'"

### 解決方法 1：安裝依賴

```bash
pip install -r requirements.txt
```

或單獨安裝 uvicorn：
```bash
pip install uvicorn[standard]
```

### 解決方法 2：檢查 Python 環境

```bash
# 檢查 uvicorn 是否已安裝
python3 -m pip show uvicorn

# 如果沒有，安裝它
python3 -m pip install uvicorn[standard]
```

## 使用 Docker（推薦）

如果遇到環境問題，使用 Docker：

```bash
docker-compose up
```

Docker 會自動處理所有依賴和環境配置。

## 常見問題

### Q: 為什麼會出現 "No module named 'app'"？

A: 因為您在 `app/` 目錄內執行。請回到專案根目錄執行。

### Q: 為什麼會出現 "No module named 'uvicorn'"？

A: 因為 uvicorn 沒有安裝。執行 `pip install -r requirements.txt` 安裝所有依賴。

### Q: 資料庫連接失敗怎麼辦？

A: 這是正常的，如果資料庫未啟動。系統會繼續運行，只是資料不會持久化。要使用資料庫，請啟動 PostgreSQL 或使用 Docker Compose。
