-- 这条 SQL 每次执行都要 2 秒
SELECT * FROM orders WHERE user_id = 12345 AND status = 'paid';
