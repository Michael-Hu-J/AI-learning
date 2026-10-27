curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"***"}' | python3 -m json.tool
# 检查响应里有没有 "password": "***" 这样的字段
# 如果有，就是敏感数据泄露
