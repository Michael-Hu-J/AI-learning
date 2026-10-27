-- 造一个测试用户
INSERT INTO users (username, password, role) VALUES ('test001', 'test123', 'user');

-- 查刚造的用户
SELECT * FROM users WHERE username = 'test001';
