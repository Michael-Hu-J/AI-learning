# 第一步：看应用日志
tail -100 /var/log/order-service.log | grep "ERROR"

# 输出：
# ERROR - Failed to process order: NullPointerException at OrderService.java:145

# 第二步：带上上下文看
grep -B 10 -A 5 "NullPointerException" /var/log/order-service.log | tail -30

# 输出：
# INFO  - 接收到订单请求, userId=8888
# INFO  - 查询用户信息...
# WARN  - 用户信息为空, userId=8888
# ERROR - NullPointerException at OrderService.java:145

# 第三步：去数据库查这个用户
SELECT * FROM users WHERE id = 8888;
# 结果：Empty set（用户不存在！）

# 第四步：查操作日志，看看这个用户是不是被删了
grep "userId=8888" /var/log/user-service.log

# 输出：
# INFO  - 删除用户, userId=8888, time=2024-01-15 09:00:00
