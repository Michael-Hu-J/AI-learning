# 试 AND 1=1
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "'\'' AND 1=1 --", "password": "***"}'

# 试 AND 1=2
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "'\'' AND 1=2 --", "password": "***"}'
