-- 查商品
SELECT * FROM products LIMIT 10;

-- 造用户
INSERT INTO users (username, password, role) VALUES ('test001', 'test123', 'user');

-- 查用户
SELECT * FROM users WHERE username = 'test001';

-- 删用户
DELETE FROM users WHERE username = 'test001';
