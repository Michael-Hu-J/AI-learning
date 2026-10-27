import requests

# 用一个公开的测试接口
url = "https://httpbin.org/post"
data = {"userId": 100, "productId": 1, "quantity": 2}

# 发送 POST 请求
response = requests.post(url, json=data)

# 打印结果
print(f"状态码: {response.status_code}")
print(f"响应体: {response.json()}")

# 断言
assert response.status_code == 200, f"预期 200，实际 {response.status_code}"
print("✅ 测试通过")
