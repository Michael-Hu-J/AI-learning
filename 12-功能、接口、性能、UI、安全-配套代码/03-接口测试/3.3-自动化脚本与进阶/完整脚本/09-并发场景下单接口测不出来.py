import requests
import threading

url = "http://test-api.example.com/api/v1/order/create"
headers = {"Authorization": "Bearer token"}
data = {"productId": 999, "quantity": 1}  # 库存只有 1

results = []

def place_order(user_id):
    data["userId"] = user_id
    response = requests.post(url, json=data, headers=headers)
    results.append(response.json())

# 两个线程同时下单
t1 = threading.Thread(target=place_order, args=(100,))
t2 = threading.Thread(target=place_order, args=(200,))

t1.start()
t2.start()
t1.join()
t2.join()

# 检查：应该只有一个成功
success_count = sum(1 for r in results if r.get("code") == 0)
assert success_count == 1, f"超卖！成功创建 {success_count} 个订单"
