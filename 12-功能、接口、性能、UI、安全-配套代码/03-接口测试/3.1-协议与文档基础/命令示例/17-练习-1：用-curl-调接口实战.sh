# 1. GET 请求：查用户
curl -v http://httpbin.org/get?user_id=100

# 2. POST 请求：提交数据
curl -X POST http://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "张三", "age": 28}'

# 3. 看响应状态码（只看状态码）
curl -s -o /dev/null -w "%{http_code}" http://httpbin.org/get
