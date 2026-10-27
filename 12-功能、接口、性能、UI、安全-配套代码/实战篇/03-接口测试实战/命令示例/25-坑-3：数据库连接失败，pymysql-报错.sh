# 1. 确认 MySQL 在不在
mysql -u root -p -e "SELECT 1"
# 能执行 → MySQL 正常

# 2. 确认数据库存在
mysql -u root -p -e "SHOW DATABASES;"
# 找找有没有 seckill_finance_db

# 3. 确认密码
# 打开 .env 文件，看 DB_PASSWORD 是什么
cat .env | grep DB_PASSWORD
# 用这个密码登录
mysql -u root -p你的密码 -e "SELECT 1"
