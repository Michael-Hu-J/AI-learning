# 第一步：拿到用户的订单号（比如 12345）

# 第二步：搜这个订单的完整日志
grep "orderId=12345" /var/log/order-service.log

# 输出：
# 10:23:45 INFO - 创建订单成功, orderId=12345
# 10:23:45 INFO - 调用支付接口, orderId=12345
# 10:23:46 ERROR - 支付失败, orderId=12345, error=Connection refused

# 第三步：看到 "Connection refused"，说明支付接口连不上

# 第四步：去支付服务的日志里看看发生了什么
grep "10:23:4[5-6]" /var/log/pay-service.log | grep "ERROR"

# 输出：
# 10:23:46 ERROR - 数据库连接池已满, active=50, max=50

# 第五步：定位到了——数据库连接池满了
