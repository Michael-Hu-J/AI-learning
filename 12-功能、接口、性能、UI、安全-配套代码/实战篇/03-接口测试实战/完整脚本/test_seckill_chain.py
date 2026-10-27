import requests
import pymysql
import json

BASE = "http://localhost:5000"

# ====== 1. 读源码找到数据库配置 ======
# 打开 .env，找 DB_HOST、DB_PASSWORD、DB_NAME
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "seckill_finance_db"
}

# ====== 2. 登录 ======
# 源码：app.py 第 307 行
resp = requests.post(f"{BASE}/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
assert resp.status_code == 200, f"登录失败: {resp.text}"
token = resp.json()["token"]
print(f"✅ 登录成功，token={token[:20]}...")

headers = {"Authorization": f"Bearer {token}"}

# ====== 3. 查抢购列表 ======
# 源码：app.py 第 495 行
resp = requests.get(f"{BASE}/api/seckill/list")
assert resp.status_code == 200
products = resp.json()
if not products:
    print("❌ 没有抢购活动，请先创建一个抢购活动")
    exit(1)

product_id = products[0]["product_id"]
current_stock = products[0]["current_stock"]
print(f"✅ 抢购商品ID={product_id}，当前库存={current_stock}")

# ====== 4. 抢购下单 ======
# 源码：app.py 第 649 行
resp = requests.post(f"{BASE}/api/seckill/order",
    json={"productId": product_id},
    headers=headers)

if resp.status_code == 201:
    order_no = resp.json()["order_no"]
    print(f"✅ 抢购成功，订单号={order_no}")

    # ====== 5. 数据库双重验证 ======
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 查 seckill_orders 表
    cursor.execute("SELECT status FROM seckill_orders WHERE order_no=%s", (order_no,))
    result = cursor.fetchone()
    print(f"🔍 seckill_orders 表状态: {result}")
    assert result and result[0] == "created", "抢购订单表状态不对！"
    
    # 查 orders 表
    cursor.execute("SELECT status FROM orders WHERE order_no=%s", (order_no,))
    result = cursor.fetchone()
    print(f"🔍 orders 表状态: {result}")
    assert result and result[0] == "pending", "普通订单表状态不对！"
    
    cursor.close()
    conn.close()
    print("✅ 数据库验证通过")
else:
    print(f"❌ 抢购失败: {resp.json()}")

# ====== 6. 重复下单验证（源码：app.py 第 691 行）=====
resp = requests.post(f"{BASE}/api/seckill/order",
    json={"productId": product_id},
    headers=headers)
assert resp.status_code == 400
assert "已参与" in resp.json().get("error", "")
print("✅ 重复下单被拦截（幂等性验证通过）")
