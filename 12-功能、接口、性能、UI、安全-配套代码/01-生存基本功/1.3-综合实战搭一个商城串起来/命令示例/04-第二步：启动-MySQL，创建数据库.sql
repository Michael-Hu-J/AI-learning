# 启动 MySQL
sudo service mysql start

# 登录 MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE mall_test DEFAULT CHARSET utf8mb4;

# 切换到这个数据库
USE mall_test;

# 创建用户表
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    status INT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

# 创建订单表
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'created',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

# 插入测试数据
INSERT INTO users (name, phone) VALUES ('测试用户1', '13900139001');
INSERT INTO users (name, phone) VALUES ('测试用户2', '13900139002');

INSERT INTO orders (user_id, amount, status) VALUES (1, 99.9, 'created');
INSERT INTO orders (user_id, amount, status) VALUES (1, 199.0, 'paid');
