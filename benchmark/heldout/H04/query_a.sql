WITH pay AS (
    SELECT order_id, SUM(payment_value) AS paid
    FROM order_payments
    GROUP BY order_id
)
SELECT SUM(oi.price) AS metric
FROM order_items oi
JOIN pay ON pay.order_id = oi.order_id
