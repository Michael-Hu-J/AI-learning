# 进入 MySQL 容器
docker exec -it seckill_finance_system-mysql-1 mysql -u root -pseckill123

# 看慢查询
SHOW PROCESSLIST;
# 发现大量 waiting for table metadata lock
