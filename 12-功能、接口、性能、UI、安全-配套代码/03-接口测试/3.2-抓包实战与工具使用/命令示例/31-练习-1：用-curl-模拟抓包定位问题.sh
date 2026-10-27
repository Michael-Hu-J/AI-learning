# 模拟场景：用户登录失败
# 1. 先发一个正常的登录请求
curl -v -X POST http://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin1234"}'

# 2. 再看响应的内容
# 注意观察：请求头（Content-Type）、请求体（数据格式）
# 响应状态码（200/400/401...）
