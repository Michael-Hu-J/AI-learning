# 1. 先创建订单
create_response = client.post("/api/v1/order/create", {
    "userId": 100,
    "items": [{"productId": 12345, "quantity": 1}]
})
order_id = create_response.json()["data"]["orderId"]

# 2. 再支付订单
pay_response = client.post("/api/v1/order/pay", {
    "orderId": order_id,
    "paymentMethod": "alipay"
})

assert pay_response.json()["data"]["status"] == "paid"
