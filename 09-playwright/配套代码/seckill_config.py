"""秒杀财务系统 UI 自动化默认配置（可通过环境变量覆盖）。"""
import os

SECKILL_BASE_URL = os.environ.get("SECKILL_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
DEFAULT_USERNAME = os.environ.get("SECKILL_USERNAME", "admin")
DEFAULT_PASSWORD = os.environ.get("SECKILL_PASSWORD", "admin123")

LOGIN_URL = f"{SECKILL_BASE_URL}/login"
PRODUCTS_URL = f"{SECKILL_BASE_URL}/products"
