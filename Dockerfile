# 使用官方 Python 3.11 作為基礎映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式檔案
COPY part_time_jobs.py .

# 暴露端口
# 3000: LINE Bot (Flask)
# 8880: FastAPI
EXPOSE 3000 8880

# 設定環境變數（可在 docker-compose.yml 或運行時覆蓋）
ENV PYTHONUNBUFFERED=1

# 啟動應用程式
CMD ["python", "part_time_jobs.py"]
