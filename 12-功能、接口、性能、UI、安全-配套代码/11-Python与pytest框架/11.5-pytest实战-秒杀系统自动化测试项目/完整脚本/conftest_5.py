"""全局配置与 fixture"""
import pytest
import json
import os
from utils.api_client import ApiClient
from utils.db_helper import DbHelper

# 加载配置
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# ---- API 客户端相关 fixture ----

@pytest.fixture(scope="session")
def base_url():
    return CONFIG["base_url"]

@pytest.fixture(scope="session")
def api(base_url):
    """不带认证的 API 客户端"""
    return ApiClient(base_url)

@pytest.fixture(scope="session")
def admin_api(base_url):
    """已登录 admin 的 API 客户端"""
    client = ApiClient(base_url)
    resp = client.post("/api/auth/login", json=CONFIG["admin_user"])
    assert resp.status_code == 200
    token = resp.json().get("token")
    if token:
        client.set_token(token)
    return client

@pytest.fixture(scope="session")
def user_api(base_url):
    """已登录普通用户的 API 客户端"""
    client = ApiClient(base_url)
    resp = client.post("/api/auth/login", json=CONFIG["normal_user"])
    assert resp.status_code == 200
    token = resp.json().get("token")
    if token:
        client.set_token(token)
    return client

# ---- 数据库 fixture ----

@pytest.fixture(scope="session")
def db():
    """数据库连接"""
    db_config = CONFIG["database"]
    helper = DbHelper(**db_config)
    yield helper
    helper.close()

# ---- 测试数据 fixture ----

@pytest.fixture
def login_cases():
    with open(f"{os.path.dirname(__file__)}/test_data/login_cases.json", 
              "r", encoding="utf-8") as f:
        return json.load(f)

# ---- 自动清理 fixture ----

@pytest.fixture
def clean_product(admin_api):
    """创建一个测试商品并自动清理"""
    resp = admin_api.post("/api/products", 
                         json={"name": "临时测试商品", "price": 99.99})
    assert resp.status_code == 200
    product_id = resp.json()["data"]["id"]
    
    yield product_id
    
    # 清理
    admin_api.delete(f"/api/products/{product_id}")
