-- 假设这条 SQL 很慢
SELECT * FROM orders WHERE user_id = 12345 AND status = 'paid';

-- 看看有没有索引
EXPLAIN SELECT * FROM orders WHERE user_id = 12345 AND status = 'paid';
-- 如果 type=ALL（全表扫描）→ 没索引

-- 加索引
CREATE INDEX idx_user_status ON orders(user_id, status);

-- 再查一次看效果
EXPLAIN SELECT * FROM orders WHERE user_id = 12345 AND status = 'paid';
-- 现在 type=ref（索引扫描），快了几百倍
