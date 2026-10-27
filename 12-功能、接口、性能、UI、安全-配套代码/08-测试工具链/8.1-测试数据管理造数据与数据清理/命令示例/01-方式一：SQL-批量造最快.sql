-- 造 100 个用户
INSERT INTO users (name, phone, email, status)
SELECT
    CONCAT('测试用户', seq),
    CONCAT('139', LPAD(seq, 8, '0')),
    CONCAT('test', seq, '@test.com'),
    1
FROM (
    SELECT 1 as seq UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
    UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
    -- ... 写到 100
) t;

-- 更简单的方式：用存储过程
DELIMITER $$
CREATE PROCEDURE create_test_users(IN count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= count DO
        INSERT INTO users (name, phone, email, status)
        VALUES (
            CONCAT('测试用户', i),
            CONCAT('139', LPAD(i, 8, '0')),
            CONCAT('test', i, '@test.com'),
            1
        );
        SET i = i + 1;
    END WHILE;
END$$
DELIMITER ;

-- 调用
CALL create_test_users(1000);
