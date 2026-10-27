# 请求一个不存在的接口
response = requests.get("http://localhost:5001/not-exist")
data = response.json()  # ❌ 这里崩了！返回的不是 JSON
