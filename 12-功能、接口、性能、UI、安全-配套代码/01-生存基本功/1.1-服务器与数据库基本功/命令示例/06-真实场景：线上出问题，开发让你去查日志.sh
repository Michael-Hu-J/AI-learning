# 第一步：实时看日志
tail -f /var/log/order-service.log

# 第二步：让开发在测试环境重新下一个单
# 你这边就能看到日志实时输出

# 第三步：如果日志太多，直接搜错误
grep "ERROR" /var/log/order-service.log | tail -20

# 第四步：看到具体报错后，复制错误信息，带上下文看
grep -C 10 "Connection refused" /var/log/order-service.log
