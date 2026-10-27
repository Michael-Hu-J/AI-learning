# 1. 检查 MySQL 容器是否在运行
docker ps | grep mysql

# 2. 如果 MySQL 跑在 Docker 里，连 127.0.0.1 可能连不上
# 改成从容器内部连：先进入容器
docker exec -it seckill_mysql_1 mysql -u root -p123456

# 3. 或者确认端口映射：本机的 3306 映射到容器的 3306
# 如果改过端口映射（比如 3307:3306），脚本里要连 3307
