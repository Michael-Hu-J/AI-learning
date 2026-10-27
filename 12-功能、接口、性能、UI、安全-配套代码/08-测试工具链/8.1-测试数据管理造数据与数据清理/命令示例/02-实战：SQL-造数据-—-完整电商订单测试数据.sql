-- 1. 造测试用户
INSERT INTO users (id, name, phone, level, created_at)
VALUES 
  (99901, '测试用户A', '13900000001', '白银', NOW()),
  (99902, '测试用户B', '13900000002', '黄金', NOW());

-- 2. 造测试商品（不同品类）
INSERT INTO products (id, name, price, stock, category)
VALUES
  (88801, '测试手机', 2999.00, 100, '数码'),
  (88802, '测试耳机', 199.00, 500, '配件'),
  (88803, '测试书籍', 59.00, 0, '图书');   -- 库存为0，测缺货场景

-- 3. 造订单（覆盖不同状态）
INSERT INTO orders (id, user_id, total_amount, status, created_at)
VALUES
  (77701, 99901, 2999.00, 'PAID',    '2025-05-01 10:00:00'),  -- 已支付
  (77702, 99901, 199.00,  'SHIPPED', '2025-05-02 14:30:00'),  -- 已发货
  (77703, 99902, 59.00,   'CANCELLED', '2025-05-03 09:15:00'),-- 已取消
  (77704, 99902, 3198.00, 'REFUNDING', '2025-05-04 16:45:00');-- 售后中

-- 4. 造订单明细
INSERT INTO order_items (order_id, product_id, quantity, price)
VALUES
  (77701, 88801, 1, 2999.00),
  (77702, 88802, 1, 199.00),
  (77703, 88803, 1, 59.00),
  (77704, 88801, 1, 2999.00),
  (77704, 88802, 1, 199.00);

-- 5. 验证：查用户 99901 的所有订单
SELECT o.id, o.status, o.total_amount, p.name, oi.quantity
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
WHERE o.user_id = 99901;

-- 6. 清理（测完执行）
-- DELETE FROM order_items WHERE order_id IN (77701, 77702, 77703, 77704);
-- DELETE FROM orders WHERE id IN (77701, 77702, 77703, 77704);
-- DELETE FROM products WHERE id IN (88801, 88802, 88803);
-- DELETE FROM users WHERE id IN (99901, 99902);
