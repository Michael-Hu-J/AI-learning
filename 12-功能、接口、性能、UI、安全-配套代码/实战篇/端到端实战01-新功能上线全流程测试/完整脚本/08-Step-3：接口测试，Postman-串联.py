import requests

BASE = "http://localhost:5001"

# 1. 注册黄金会员
resp = requests.post(f"{BASE}/api/auth/register", json={
    "username": "黄金测试",
    "password": "Test123456",
    "level": "黄金"
})
token = resp.json()["data"]["token"]

# 2. 下单
headers = {"Authorization": f"Bearer {token}"}
resp = requests.post(f"{BASE}/api/orders", json={
    "product_id": 1,
    "quantity": 1
}, headers=headers)
order_id = resp.json()["data"]["id"]

# 3. 验证订单金额
resp = requests.get(f"{BASE}/api/orders/{order_id}", headers=headers)
order = resp.json()["data"]
assert order["total_amount"] == 90.0, f"预期90元，实际{order['total_amount']}元"
assert order["original_amount"] == 100.0, f"预期原价100元，实际{order['original_amount']}元"
print("✅ 黄金会员9折测试通过")
