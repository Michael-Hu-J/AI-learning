-- 先不加索引，跑一次
SELECT * FROM orders WHERE status = 'paid' AND create_time > '2025-01-01';

-- 加组合索引后再跑一次
CREATE INDEX idx_status_time ON orders(status, create_time);
SELECT * FROM orders WHERE status = 'paid' AND create_time > '2025-01-01';
