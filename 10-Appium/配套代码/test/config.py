
"""
系统配置 — 被测试系统地址
"""
import os

# 被测试系统地址（Demo 改端口时同步设置 MOCK_SERVER_PORT 或 MOCK_SERVER_URL）
_port = os.environ.get("MOCK_SERVER_PORT", "5001")
MOCK_SERVER_URL = os.environ.get("MOCK_SERVER_URL", f"http://127.0.0.1:{_port}")
