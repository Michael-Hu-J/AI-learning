# 用 Postman 或 curl 测试折扣接口
curl -X POST http://localhost:5001/api/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id": 99901, "product_id": 88801, "quantity": 1}'

# 验证返回的订单金额是否正确
mysql -u root -p -e "SELECT id, total_amount, discount_amount FROM orders WHERE user_id = 99901 ORDER BY id DESC LIMIT 1;"
