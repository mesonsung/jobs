# ==================== 構建階段 ====================
FROM python:3.11-alpine AS builder

# 設定工作目錄
WORKDIR /app

# 安裝構建依賴
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    g++ \
    musl-dev \
    postgresql-dev \
    linux-headers

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴到臨時目錄
RUN pip install --no-cache-dir --no-compile --user -r requirements.txt

# 清理構建依賴
RUN apk del .build-deps

# ==================== 運行階段 ====================
FROM python:3.11-alpine

# 設定工作目錄
WORKDIR /app

# 安裝運行時依賴（僅 PostgreSQL 客戶端庫）
RUN apk add --no-cache \
    postgresql-libs \
    && rm -rf /var/cache/apk/*

# 使用非 root 使用者運行（安全性最佳實踐）
RUN adduser -D -u 1000 appuser

# 從構建階段複製已安裝的 Python 套件到 appuser 目錄
COPY --from=builder /root/.local /home/appuser/.local

# 確保 Python 可以找到本地安裝的套件
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 複製應用程式檔案
COPY app/ ./app/
COPY part_time_jobs.py .
COPY main.py .

# 設定檔案所有權
RUN chown -R appuser:appuser /app /home/appuser/.local

# 暴露端口
# 3000: LINE Bot (Flask)
# 8880: FastAPI
EXPOSE 3000 8880

# 切換到非 root 使用者
USER appuser

# 啟動應用程式
# 使用新的模組化結構
# 在生產環境中，設置環境變數以使用 Gunicorn
ENV DEBUG=false
ENV USE_GUNICORN=true
ENV GUNICORN_WORKERS=2
ENV LOG_LEVEL=info

# 使用 Gunicorn 啟動（通過 Python 模組）
CMD ["python", "-m", "app.main"]
