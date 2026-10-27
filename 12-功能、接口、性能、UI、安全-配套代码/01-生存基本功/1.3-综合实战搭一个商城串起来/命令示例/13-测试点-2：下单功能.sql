-- 测试场景：用户下单
-- 前置条件：用户 1 已有 2 个订单

-- 执行下单
INSERT INTO orders (user_id, amount, status) VALUES (1, 50.0, 'created');

-- 验证 1：用户 1 应该有 3 个订单
SELECT COUNT(*) FROM orders WHERE user_id = 1;
-- 预期：3

-- 验证 2：新订单状态是 created
SELECT status FROM orders WHERE amount = 50.0;
-- 预期：created

-- 验证 3：无效用户下单（user_id=999 不存在）
INSERT INTO orders (user_id, amount, status) VALUES (999, 10.0, 'created');
-- 预期：ERROR 1452 (23000): Cannot add or update a child row — 外键约束生效
