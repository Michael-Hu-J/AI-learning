import requests
import json

# 接口地址
url = "http://test-api.example.com/api/v1/order/create"

# 请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your_token_here"
}

# 请求体
data = {
    "userId": 100,
    "items": [
        {"productId": 12345, "quantity": 2},
        {"productId": 67890, "quantity": 1}
    ],
    "addressId": 56
}

# 发送请求
response = requests.post(url, json=data, headers=headers)

# 打印结果
print(f"状态码: {response.status_code}")
print(f"响应体: {response.json()}")

# 断言
assert response.status_code == 200, f"预期 200，实际 {response.status_code}"
result = response.json()
assert result["code"] == 0, f"预期 code=0，实际 code={result['code']}"
assert "orderId" in result["data"], "响应中缺少 orderId"
