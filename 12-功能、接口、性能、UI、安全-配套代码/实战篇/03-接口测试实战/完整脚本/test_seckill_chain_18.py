import requests
import threading

BASE = "http://localhost:5000"
PRODUCT_ID = 1  # 改成你的商品ID
CONCURRENT = 200  # 200 并发

# 先登录拿 token
resp = requests.post(f"{BASE}/api/auth/login",
    json={"username": "admin", "password": "admin123"})
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

success_count = 0
fail_count = 0
lock = threading.Lock()

def seckill():
    global success_count, fail_count
    resp = requests.post(f"{BASE}/api/seckill/order",
        json={"productId": PRODUCT_ID},
        headers=headers)
    with lock:
        if resp.status_code == 201:
            success_count += 1
            print(f"🔥 抢购成功: {resp.json()['order_no']}")
        else:
            fail_count += 1
            if fail_count <= 5:  # 只打印前5个失败
                print(f"❌ 抢购失败: {resp.json()}")

# 200 并发
threads = []
for i in range(CONCURRENT):
    t = threading.Thread(target=seckill)
    threads.append(t)

for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"\n{'='*50}")
print(f"并发结果: 成功={success_count}, 失败={fail_count}")

# ====== 读源码验证 ======
# 打开 seckill_service.py 第 61 行：
# remaining_stock = atomic_decrease_stock(activity_id, product_id)
#
# 打开 redis_client.py 搜索 atomic_decrease_stock：
# 它用 Lua 脚本 ACQUIRE_DECREASE 实现原子扣减
# 源码：
# lua_script = """
# local stock = redis.call(\"DECR\", KEYS[1])
# if stock >= 0 then
#     return stock
# else
#     redis.call(\"INCR\", KEYS[1])
#     return -1
# end
# """
#
# 关键：DECR 是 Redis 原子命令，200 并发也只扣到 -1 就被 INCR 恢复。
# 所以不会超卖。

if success_count <= 5 and success_count >= 0:
    print(f"✅ 没有超卖！成功{success_count}个 ≤ 库存5")
else:
    print(f"⚠️ 可能超卖！成功{success_count}个，库存才5")
