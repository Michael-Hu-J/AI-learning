docker exec -it seckill_mysql_1 mysql -u root -p123456 seckill_finance_db \
  -e "SELECT count(*) FROM users;"
