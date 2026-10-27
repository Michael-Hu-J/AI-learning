# 1. 确认 schema.sql 有没有执行
# 检查表结构
docker exec -it seckill_mysql_1 mysql -u root -p123456 seckill_finance_db \
  -e "SHOW TABLES;"

# 2. 如果没表，手动执行 schema.sql
docker exec -i seckill_mysql_1 mysql -u root -p123456 seckill_finance_db < schema.sql
