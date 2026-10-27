"""
测试秒杀系统 - 商品管理模块
"""
import pytest
import requests

# 全局配置
BASE_URL = "http://localhost:5001"

# ---- fixtures ----

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture(scope="session")
def admin_token(base_url):
    resp = requests.post(f"{base_url}/api/auth/login",
                        json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["token"]

# ---- 测试用例 ----

def test_create_product(admin_token, base_url):
    """正常创建商品"""
    resp = requests.post(f"{base_url}/api/products",
                        json={"name": "测试商品", "price": 99.99},
                        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "测试商品"

@pytest.mark.parametrize("name, price, expect_code", [
    ("",      99.99, 400),   # 名称为空
    ("商品",  -1,    400),   # 价格为负
    ("商品",  0,     400),   # 价格为 0
    ("a" * 101, 99.99, 400), # 名称超长
])
def test_create_product_invalid(admin_token, base_url, name, price, expect_code):
    """创建商品-异常场景"""
    resp = requests.post(f"{base_url}/api/products",
                        json={"name": name, "price": price},
                        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == expect_code

def test_delete_product(admin_token, base_url):
    """删除不存在的商品"""
    resp = requests.delete(f"{base_url}/api/products/99999",
                          headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 404
