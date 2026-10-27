# 故意触发 500
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": null, "password": null}'
# 如果返回了 Python 报错堆栈 → 错误信息泄露
# 如果返回 {"error": "服务器内部错误"} → 安全
