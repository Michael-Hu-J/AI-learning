import requests

url = "https://httpbin.org/post"
data = {"username": "admin", "password": "Admin1234"}

response = requests.post(url, json=data)
result = response.json()

# 1. 断言状态码
assert response.status_code == 200

# 2. 断言返回数据的结构
assert "json" in result, "响应中缺少 json 字段"

# 3. 断言具体数据
assert result["json"]["username"] == "admin"

print("✅ 三层断言都通过了")
