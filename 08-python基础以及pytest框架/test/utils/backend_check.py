"""检测秒杀演示后端是否可用（/api/auth/login）。"""
import os

import requests


def seckill_api_available() -> bool:
    base = os.getenv(
        "SECKILL_BASE_URL",
        os.getenv("TEST_BASE_URL", "http://localhost:5000"),
    ).rstrip("/")
    password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")
    try:
        resp = requests.post(
            f"{base}/api/auth/login",
            json={"username": "admin", "password": password},
            timeout=3,
        )
        if resp.status_code != 200:
            return False
        data = resp.json()
        return bool(data.get("token") or data.get("access_token"))
    except Exception:
        return False
