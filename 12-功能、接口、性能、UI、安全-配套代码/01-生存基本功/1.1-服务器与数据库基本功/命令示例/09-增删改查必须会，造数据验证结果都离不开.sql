-- 查：看看数据长什么样
SELECT * FROM users WHERE phone = '13800138000';

-- 查：看看有多少条
SELECT COUNT(*) FROM orders WHERE status = 'paid';

-- 查：看最近创建的
SELECT * FROM orders ORDER BY create_time DESC LIMIT 10;

-- 插：造一条测试数据
INSERT INTO users (name, phone, email) VALUES ('测试用户', '13900139000', 'test@test.com');

-- 改：修改某个用户的状态
UPDATE users SET status = 1 WHERE phone = '13900139000';

-- 删：删除测试数据（⚠️ 一定要加 WHERE）
DELETE FROM users WHERE phone = '13900139000';
