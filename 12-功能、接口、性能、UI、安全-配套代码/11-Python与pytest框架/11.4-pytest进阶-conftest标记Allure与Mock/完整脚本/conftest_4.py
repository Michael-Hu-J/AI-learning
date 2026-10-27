# conftest.py
import pytest
import requests

@pytest.fixture
def test_product(base_url, admin_token):
    """创建一个测试商品，用完后自动删除"""
    # setup：创建商品
    resp = requests.post(f"{base_url}/api/products",
                        json={"name": "临时测试商品", "price": 99.99},
                        headers={"Authorization": f"Bearer {admin_token}"})
    product_id = resp.json()["data"]["id"]
    
    yield product_id  # 返回商品 ID 给测试用例
    
    # teardown：删除商品
    requests.delete(f"{base_url}/api/products/{product_id}",
                   headers={"Authorization": f"Bearer {admin_token}"})
    print(f"已清理测试商品：{product_id}")

# 使用
def test_create_order(base_url, user_token, test_product):
    """创建一个包含测试商品的订单"""
    resp = requests.post(f"{base_url}/api/orders",
                        json={"product_id": test_product, "quantity": 2},
                        headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    # 用例结束 → pytest 自动执行 yield 后面的清理代码
