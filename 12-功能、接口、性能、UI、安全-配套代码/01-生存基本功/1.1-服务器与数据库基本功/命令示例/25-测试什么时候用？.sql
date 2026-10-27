SELECT user_id, amount, order_time
FROM (
    SELECT user_id, amount, order_time,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_time ASC) as rn
    FROM orders
) t
WHERE rn = 1;
