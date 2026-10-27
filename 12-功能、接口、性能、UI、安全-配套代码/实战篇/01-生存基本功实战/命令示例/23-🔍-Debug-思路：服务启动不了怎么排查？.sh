# 第1步：看容器状态
docker ps -a
# STATUS 列如果是 Exited，说明容器启动后挂了
# 如果是 Restarting，说明在反复重启

# 第2步：看容器日志（最关键的线索）
docker logs seckill_app_1      # 应用日志
docker logs seckill_mysql_1    # MySQL 日志
docker logs seckill_redis_1    # Redis 日志

# 第3步：看端口是否被占用
netstat -tlnp | grep -E '3306|5000|6379'

# 第4步：看资源够不够
docker stats
free -h
df -h

# 第5步：如果是 MySQL 连不上
docker exec seckill_mysql_1 mysql -u root -p123456 -e "SELECT 1"
# 能返回 1，说明 MySQL 正常；报错就看报错信息

# 第6步：如果应用连不上 MySQL
# 检查 docker-compose.yml 里的 DB_HOST 是不是容器名 "mysql"
# 不能写成 "localhost" 或 "127.0.0.1"（容器之间用容器名通信）

# 第7步：重启大法（确认不是数据损坏）
docker-compose down
docker-compose up -d
