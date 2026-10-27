-- 加组合索引
CREATE INDEX idx_user_status ON orders(user_id, status);

-- 加完后用 EXPLAIN 确认
EXPLAIN SELECT * FROM orders WHERE user_id = 12345 AND status = 'paid';
-- 现在 type 应该变成 ref，rows 降到个位数
