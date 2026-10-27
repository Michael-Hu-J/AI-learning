# 确认测试环境可用
docker ps
# 应该看到 mysql、redis、app 三个容器都在运行

# 确认数据库版本
mysql -u root -p -e "SELECT VERSION();"
# 确认跟生产一致

# 确认 Redis 版本
redis-cli -h 127.0.0.1 -p 6381 INFO server | grep redis_version
