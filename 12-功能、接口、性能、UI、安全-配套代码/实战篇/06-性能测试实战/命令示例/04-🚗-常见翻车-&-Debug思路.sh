# 1. 先降并发数，确认系统能恢复
# 2. 从10并发开始，逐步增加，别一步到位
# 3. 检查 MySQL 最大连接数
docker exec seckill_mysql_1 mysql -u root -p123456 \
  -e "SHOW VARIABLES LIKE 'max_connections';"
# 默认是 151，如果你起 200 个线程，MySQL 会拒绝多余的连接
