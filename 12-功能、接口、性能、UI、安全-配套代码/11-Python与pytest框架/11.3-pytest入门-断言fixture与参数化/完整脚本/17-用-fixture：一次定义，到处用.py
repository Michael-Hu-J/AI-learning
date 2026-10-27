import pytest
import requests

@pytest.fixture
def admin_token():
    """提供 admin 账号的 token"""
    resp = requests.post("http://localhost:5001/api/auth/login",
                        json={"username": "admin", "password": "admin123"})
    token = resp.json()["token"]
    yield token  # yield 返回，执行完用例后继续收尾
    # 这里可以做清理工作（如有需要）
    print("用例执行完毕，清理...")

def test_create_product(admin_token):  # 参数名 = fixture 函数名
    """创建商品"""
    resp = requests.post("http://localhost:5001/api/products",
                        json={"name": "手机", "price": 2999},
                        headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

def test_get_products(admin_token):
    """查询商品列表"""
    resp = requests.get("http://localhost:5001/api/products",
                       headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
