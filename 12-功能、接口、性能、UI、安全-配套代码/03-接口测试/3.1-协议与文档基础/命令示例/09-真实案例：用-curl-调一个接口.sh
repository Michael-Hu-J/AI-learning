# 最简单的 GET 请求
curl http://api.example.com/api/v1/users/100

# 带 Token 的 GET 请求
curl -H "Authorization: Bearer your_token_here" \
     http://api.example.com/api/v1/users/100

# POST 请求（创建订单）
curl -X POST http://api.example.com/api/v1/order/create \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer your_token_here" \
     -d '{
           "userId": 100,
           "items": [{"productId": 12345, "quantity": 2}],
           "addressId": 56
         }'
