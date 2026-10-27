import pytest
import requests
import json
import os

# 加载配置文件
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

@pytest.fixture(scope="session")
def base_url():
    return CONFIG["base_url"]

@pytest.fixture(scope="session")
def admin_token(base_url):
    resp = requests.post(f"{base_url}/api/auth/login",
                        json=CONFIG["admin_user"])
    assert resp.status_code == 200
    return resp.json()["token"]

@pytest.fixture
def auth_header(admin_token):
    """返回认证头，方便每个用例直接用"""
    return {"Authorization": f"Bearer {admin_token}"}

@pytest.fixture(scope="session")
def db_config():
    """数据库配置，供数据验证使用"""
    return CONFIG["database"]
