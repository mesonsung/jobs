#!/bin/bash
# 測試執行腳本

echo "=== 檢查執行環境 ==="
echo "當前目錄: $(pwd)"
echo "Python 版本: $(python3 --version)"
echo ""

echo "=== 檢查依賴 ==="
python3 -c "import uvicorn; print('✅ uvicorn:', uvicorn.__version__)" 2>&1 || echo "❌ uvicorn 未安裝"
python3 -c "import flask; print('✅ flask:', flask.__version__)" 2>&1 || echo "❌ flask 未安裝"
python3 -c "import fastapi; print('✅ fastapi:', fastapi.__version__)" 2>&1 || echo "❌ fastapi 未安裝"
echo ""

echo "=== 檢查模組導入 ==="
python3 -c "from app.main import main; print('✅ app.main 可以導入')" 2>&1 | tail -1
echo ""

echo "=== 執行方式 ==="
echo "從當前目錄執行：python3 main.py"
echo "或使用模組方式：python3 -m app.main"
