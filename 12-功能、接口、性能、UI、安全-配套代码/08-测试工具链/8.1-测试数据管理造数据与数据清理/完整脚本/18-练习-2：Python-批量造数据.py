import requests
import random

BASE_URL = "http://test-api.example.com"
PHONE_PREFIX = "139"

# 造 20 个用户
for i in range(20):
    phone = f"{PHONE_PREFIX}{random.randint(10000000, 99999999)}"
    resp = requests.post(f"{BASE_URL}/api/v1/user/register", json={
        "name": f"批量用户{i}", "phone": phone, "password": "Test1234"
    })
    if resp.status_code == 200:
        print(f"✅ 用户 {i+1} 创建成功")
    else:
        print(f"❌ 用户 {i+1} 创建失败: {resp.status_code}")
