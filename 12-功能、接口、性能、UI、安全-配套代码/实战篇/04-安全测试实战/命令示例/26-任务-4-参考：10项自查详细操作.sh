# 先登录拿 Token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"***"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 改 Token 最后一位字符
FAKE_TOKEN="${TOKEN%?}X"

# 用假 Token 调接口
curl http://localhost:5000/api/users/1 \
  -H "Authorization: Bearer $FAKE_TOKEN"
# 预期返回 401
