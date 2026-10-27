# 1. 确认环境
uname -a && java -version && mysql --version && git --version

# 2. 创建数据库和表
mysql -u root -p -e "
CREATE DATABASE IF NOT EXISTS mall_test DEFAULT CHARSET utf8mb4;
USE mall_test;
CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50) NOT NULL, phone VARCHAR(20) UNIQUE, status INT DEFAULT 1, create_time DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE orders (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, amount DECIMAL(10,2), status VARCHAR(20) DEFAULT 'created', create_time DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(id));
INSERT INTO users (name, phone) VALUES ('用户A','13900000001'),('用户B','13900000002');
INSERT INTO orders (user_id, amount, status) VALUES (1,99.9,'created'),(1,199.0,'paid');
"
