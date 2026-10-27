# A用户的token，尝试修改B的订单
curl -X PUT http://localhost:5001/api/orders/999 \
  -H "Authorization: Bearer $TOKEN_A" \
  -d '{"status": "cancelled"}'
# 预期：返回 403 Forbidden
