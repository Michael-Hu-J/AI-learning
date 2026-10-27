curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "'\'' OR 1=1 --", "password": "***"}'
# 预期返回 401 → 安全
