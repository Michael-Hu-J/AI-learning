sudo mkdir -p /var/log/mall && sudo chmod 777 /var/log/mall
echo "2025-06-07 10:00:00 INFO 服务启动成功" >> /var/log/mall/order.log
echo "2025-06-07 10:00:01 INFO 创建订单成功 orderId=1" >> /var/log/mall/order.log
echo "2025-06-07 10:00:02 ERROR 支付失败 Connection refused" >> /var/log/mall/order.log
grep "ERROR" /var/log/mall/order.log
