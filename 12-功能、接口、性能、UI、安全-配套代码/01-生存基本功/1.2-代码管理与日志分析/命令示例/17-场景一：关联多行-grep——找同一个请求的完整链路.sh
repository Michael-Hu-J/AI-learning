# 一个订单请求，经过 order-service 和 pay-service
# 先找到 orderId
grep "创建订单" /var/log/order-service.log | tail -5

# 输出：
# 2025-06-07 10:23:45 INFO - 创建订单成功, orderId=99001

# 然后用这个 orderId 在多个服务日志里搜
grep "99001" /var/log/order-service.log
grep "99001" /var/log/pay-service.log
grep "99001" /var/log/inventory-service.log

# 三个日志拼起来，就是一个完整的请求链路
