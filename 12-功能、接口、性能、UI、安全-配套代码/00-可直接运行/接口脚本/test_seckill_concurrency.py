"""实战03 任务5：200并发抢购 — 验证防超卖"""
import requests
import threading

BASE = "http://localhost:5001"
PRODUCT_ID = 1
CONCURRENT = 200
EXPECTED_STOCK = 5

resp = requests.post(f"{BASE}/api/auth/login", json={
    "username": "admin",
    "password": "admin123",
})
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

success_count = 0
fail_count = 0
lock = threading.Lock()


def seckill():
    global success_count, fail_count
    resp = requests.post(
        f"{BASE}/api/seckill/order",
        json={"productId": PRODUCT_ID},
        headers=headers,
    )
    with lock:
        if resp.status_code in (200, 201):
            success_count += 1
            print(f"🔥 抢购成功: {resp.json().get('order_no', '')}")
        else:
            fail_count += 1
            if fail_count <= 5:
                print(f"❌ 抢购失败: {resp.json()}")


threads = [threading.Thread(target=seckill) for _ in range(CONCURRENT)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"\n{'=' * 50}")
print(f"并发结果: 成功={success_count}, 失败={fail_count}")

if success_count <= EXPECTED_STOCK:
    print(f"✅ 没有超卖！成功{success_count}个 ≤ 库存{EXPECTED_STOCK}")
else:
    print(f"⚠️ 可能超卖！成功{success_count}个，库存才{EXPECTED_STOCK}")
