# 1️⃣ 实时看日志，看有没有新报错
# 你的命令：
tail -f /var/log/order-service.log

# 2️⃣ 搜所有 ERROR 日志，只看最后 20 行
# 你的命令：
grep "ERROR" /var/log/order-service.log | tail -20

# 3️⃣ 看到一条报错 "Connection refused"，带上上下文再看
# 你的命令：
grep -C 5 "Connection refused" /var/log/order-service.log
