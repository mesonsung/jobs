# 生產環境部署指南

## 當前配置

目前系統使用 Flask 開發伺服器，會顯示以下警告：

```
WARNING: This is a development server. Do not use it in a production deployment.
```

這是正常的，因為 Flask 開發伺服器不適合生產環境。

## 生產環境建議

### 選項 1：使用 Gunicorn（推薦）

Gunicorn 是一個 Python WSGI HTTP 伺服器，適合生產環境。

#### 安裝 Gunicorn

```bash
pip install gunicorn
```

或添加到 `requirements.txt`：
```
gunicorn>=21.2.0
```

#### 修改啟動方式

創建 `gunicorn_config.py`：

```python
# gunicorn_config.py
bind = "0.0.0.0:3000"
workers = 2
worker_class = "sync"
timeout = 120
keepalive = 5
```

#### 修改 Dockerfile

```dockerfile
# 使用 gunicorn 啟動 Flask 應用
CMD ["gunicorn", "--config", "gunicorn_config.py", "app.bot.bot:app.flask_app"]
```

### 選項 2：使用 Waitress（Windows 兼容）

Waitress 是一個跨平台的 WSGI 伺服器。

#### 安裝 Waitress

```bash
pip install waitress
```

#### 修改啟動方式

在 `app/bot/bot.py` 的 `run` 方法中：

```python
from waitress import serve

def run(self, port: int = 3000, debug: bool = False, use_threading: bool = True):
    if not debug:
        # 生產環境使用 waitress
        serve(self.flask_app, host='0.0.0.0', port=port)
    else:
        # 開發環境使用 Flask 開發伺服器
        self.flask_app.run(host='0.0.0.0', port=port, debug=debug)
```

### 選項 3：抑制警告（僅開發環境）

如果只是開發環境，可以抑制警告訊息（已在代碼中實現）。

## 當前狀態

- ✅ 已添加警告抑制（開發環境）
- ⏳ 生產環境建議使用 Gunicorn 或 Waitress

## 部署檢查清單

- [ ] 使用生產級 WSGI 伺服器（Gunicorn/Waitress）
- [ ] 設置適當的 worker 數量
- [ ] 配置反向代理（Nginx）
- [ ] 啟用 HTTPS
- [ ] 設置日誌記錄
- [ ] 配置監控和告警
- [ ] 設置環境變數（不要硬編碼敏感資訊）

## 注意事項

1. **開發環境**：使用 Flask 開發伺服器是可以的
2. **生產環境**：必須使用生產級 WSGI 伺服器
3. **Docker 部署**：可以在 Dockerfile 中配置使用 Gunicorn
