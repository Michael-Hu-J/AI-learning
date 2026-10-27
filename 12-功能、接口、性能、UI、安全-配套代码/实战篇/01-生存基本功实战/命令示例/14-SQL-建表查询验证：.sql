mysql> SELECT * FROM products LIMIT 5;
+----+----------+-------+--------+---------------------+
| id | name     | price | stock  | created_at          |
+----+----------+-------+--------+---------------------+
|  1 | 手机     |  2999 |    100 | 2024-01-01 00:00:00 |
|  2 | 电脑     |  5999 |     50 | 2024-01-01 00:00:00 |
|  3 | 平板     |  1999 |     80 | 2024-01-01 00:00:00 |
+----+----------+-------+--------+---------------------+
3 rows in set (0.01 sec)

mysql> INSERT INTO users (username, password, role) VALUES ('test001', 'test123', 'user');
Query OK, 1 row affected (0.02 sec)

mysql> SELECT * FROM users WHERE username = 'test001';
+----+----------+----------+------+---------------------+
| id | username | password | role | created_at          |
+----+----------+----------+------+---------------------+
| 11 | test001  | test123  | user | 2024-06-07 10:30:00 |
+----+----------+----------+------+---------------------+
1 row in set (0.00 sec)
