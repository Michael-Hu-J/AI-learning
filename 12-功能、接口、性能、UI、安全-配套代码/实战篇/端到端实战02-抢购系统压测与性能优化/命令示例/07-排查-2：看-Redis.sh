# 进入 Redis 容器
docker exec -it seckill_finance_system-redis-1 redis-cli

# 看连接数
INFO clients
# connected_clients: 150（正常）

# 看内存
INFO memory
# used_memory: 50MB（正常）
