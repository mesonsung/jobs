"""
Good Jobs 報班系統 - 主入口點

重構後的入口點，使用新的模組化結構
"""
import sys
import os

# 確保當前目錄在 Python 路徑中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    # 使用新的模組化結構
    from app.main import main
    main()
