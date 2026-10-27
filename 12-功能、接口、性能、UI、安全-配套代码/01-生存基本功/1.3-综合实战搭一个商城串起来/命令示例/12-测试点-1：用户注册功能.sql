-- 测试场景：注册一个新用户
-- 前置条件：users 表当前有 2 条数据

-- 执行注册（模拟接口调用）
INSERT INTO users (name, phone) VALUES ('新用户', '13900139003');

-- 验证 1：用户数应该是 3
SELECT COUNT(*) FROM users;
-- 预期：3

-- 验证 2：新用户能查到
SELECT * FROM users WHERE phone = '13900139003';
-- 预期：返回 1 条记录

-- 验证 3：重复手机号注册应该失败
INSERT INTO users (name, phone) VALUES ('重复用户', '13900139003');
-- 预期：ERROR 1062 (23000): Duplicate entry '13900139003' for key 'phone'
