# 启动 MySQL
docker run -d --name test-mysql \
    -e MYSQL_ROOT_PASSWORD=*** \
    -p 3306:3306 \
    mysql:8.0

# 启动 Redis
docker run -d --name test-redis \
    -p 6379:6379 \
    redis:7.0

# 启动你的应用
docker run -d --name test-app \
    -p 8080:8080 \
    --link test-mysql:mysql \
    --link test-redis:redis \
    your-app:latest

# 看日志
docker logs -f test-app

# 停止
docker stop test-app test-mysql test-redis

# 删除
docker rm test-app test-mysql test-redis
