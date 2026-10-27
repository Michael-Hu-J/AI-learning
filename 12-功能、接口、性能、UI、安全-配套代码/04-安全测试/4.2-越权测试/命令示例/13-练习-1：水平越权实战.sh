# 用用户A的 Token 查用户B的订单
curl -X GET http://test-api.example.com/api/v1/order/101 \
  -H "Authorization: Bearer [用户A的Token]"

# 预期：403 Forbidden
# 如果返回了用户B的订单数据 → 水平越权漏洞
