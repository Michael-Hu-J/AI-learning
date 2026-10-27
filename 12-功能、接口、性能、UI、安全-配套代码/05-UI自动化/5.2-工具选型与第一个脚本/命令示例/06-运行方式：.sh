# 安装依赖
pip install pytest-playwright

# 运行测试
pytest test_playwright_first.py --headed  # 有界面模式
pytest test_playwright_first.py            # 无界面模式（CI 用）
