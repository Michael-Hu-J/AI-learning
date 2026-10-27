docker exec seckill-mysql mysql -u root -p123456 \
  -e "SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;"
