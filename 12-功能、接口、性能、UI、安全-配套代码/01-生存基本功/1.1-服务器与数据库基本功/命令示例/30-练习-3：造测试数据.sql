-- 插用户
INSERT INTO users (name, phone) VALUES ('练习用户', '13999999999');

-- 插订单
INSERT INTO orders (user_id, amount, status) VALUES (LAST_INSERT_ID(), 199.00, 'paid');

-- 验证
SELECT * FROM users WHERE phone = '13999999999';
SELECT * FROM orders WHERE user_id = (SELECT id FROM users WHERE phone = '13999999999');
