# 1. 不传 Token → 应该 401
curl -X GET http://localhost:5000/api/users/1
# 预期：401

# 2. 无效 Token → 应该 401
curl -X GET http://localhost:5000/api/users/1 \
  -H "Authorization: Bearer invalid_token"
# 预期：401

# 3. 有效 Token 但没权限 → 应该 403
# 用 testuser 的 Token 调管理员接口
curl -X GET http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer ***"
# 预期：403
