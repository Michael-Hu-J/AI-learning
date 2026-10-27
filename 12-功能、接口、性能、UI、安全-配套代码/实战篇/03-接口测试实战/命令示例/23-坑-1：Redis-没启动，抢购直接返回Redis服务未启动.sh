# 1. 确认 Redis 在不在
redis-cli ping
# 预期输出：PONG
# 如果没输出 → Redis 没启动

# 2. 启动 Redis
sudo service redis-server start
# 或
sudo systemctl start redis-server

# 3. 再验证
redis-cli ping
# 现在应该返回 PONG
