# test_auth.py — 不需要 import 任何 conftest 的内容
def test_get_products(base_url, admin_token):
    """查询商品列表"""
    resp = requests.get(f"{base_url}/api/products",
                       headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

# test_orders.py — 直接用同一个 fixture
def test_create_order(base_url, user_token):
    """用户下单"""
    resp = requests.post(f"{base_url}/api/orders",
                        json={"product_id": 1, "quantity": 1},
                        headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
