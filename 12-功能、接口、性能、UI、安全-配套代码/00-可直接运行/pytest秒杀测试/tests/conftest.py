"""全局配置与 fixture"""
import pytest
import json
import os
from utils.api_client import ApiClient
from utils.db_helper import DbHelper

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


@pytest.fixture(scope="session")
def base_url():
    return CONFIG["base_url"]


@pytest.fixture(scope="session")
def api(base_url):
    return ApiClient(base_url)


@pytest.fixture(scope="session")
def admin_api(base_url):
    client = ApiClient(base_url)
    resp = client.post("/api/auth/login", json=CONFIG["admin_user"])
    assert resp.status_code == 200
    token = resp.json().get("token")
    if token:
        client.set_token(token)
    return client


@pytest.fixture(scope="session")
def user_api(base_url):
    client = ApiClient(base_url)
    resp = client.post("/api/auth/login", json=CONFIG["normal_user"])
    assert resp.status_code == 200
    token = resp.json().get("token")
    if token:
        client.set_token(token)
    return client


@pytest.fixture(scope="session")
def db():
    helper = DbHelper(**CONFIG["database"])
    yield helper
    helper.close()


@pytest.fixture
def login_cases():
    path = os.path.join(os.path.dirname(__file__), "test_data/login_cases.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def clean_product(admin_api):
    resp = admin_api.post("/api/products", json={"name": "临时测试商品", "price": 99.99})
    assert resp.status_code == 200
    product_id = resp.json()["data"]["id"]
    yield product_id
    admin_api.delete(f"/api/products/{product_id}")
