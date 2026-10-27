import requests

# 测试登录接口
url = "http://localhost:5000/api/auth/login"
data = {"username": "admin", "password": "admin123"}
response = requests.post(url, json=data)
print(f"状态码: {response.status_code}")
print(f"响应: {response.json()}")
assert response.status_code == 200
print("✅ 登录成功")
