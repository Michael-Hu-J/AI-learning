# 测试场景：支付回调失败，怎么排查？

# 第 1 步：看有没有错误日志
grep "ERROR" /var/log/mall/order-service.log
# 输出：2024-01-15 10:00:03 ERROR [http-2] OrderService - 支付回调失败，Connection refused

# 第 2 步：看错误发生前后的日志
grep "2024-01-15 10:00:0[2-4]" /var/log/mall/order-service.log
# 能看到错误前后的完整上下文

# 第 3 步：查数据库验证订单状态
mysql -u root -e "SELECT id, status FROM mall_test.orders WHERE status = 'created';"
# 如果订单状态还是 created（没变成 paid），说明支付回调确实没成功
