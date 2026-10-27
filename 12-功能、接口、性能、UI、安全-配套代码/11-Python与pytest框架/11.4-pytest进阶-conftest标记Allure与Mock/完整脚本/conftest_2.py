# tests/conftest.py
import pytest
import requests

BASE_URL = "http://localhost:5001"

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture(scope="session")
def admin_token(base_url):
    """整个测试会话只登录一次"""
    resp = requests.post(f"{base_url}/api/auth/login",
                        json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["token"]

@pytest.fixture(scope="session")
def user_token(base_url):
    """普通用户的 token"""
    resp = requests.post(f"{base_url}/api/auth/login",
                        json={"username": "testuser", "password": "test123"})
    assert resp.status_code == 200
    return resp.json()["token"]
