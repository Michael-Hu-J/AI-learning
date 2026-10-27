# 用普通用户的Token调管理员接口
curl -X DELETE http://test-api.example.com/api/v1/admin/users/5 \
  -H "Authorization: Bearer [普通用户的Token]"

# 预期：403 Forbidden
# 如果返回了200或302 → 垂直越权漏洞
