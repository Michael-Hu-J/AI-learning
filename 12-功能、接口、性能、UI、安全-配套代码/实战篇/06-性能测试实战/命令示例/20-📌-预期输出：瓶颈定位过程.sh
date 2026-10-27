# 1. 给 product_id 加索引（如果没有的话）
ALTER TABLE products ADD INDEX idx_id (id);

# 2. 用 Redis 做库存预扣减，代替 MySQL 行锁
# 3. 批量扣减，减少数据库事务次数
