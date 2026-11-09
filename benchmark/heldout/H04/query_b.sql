SELECT SUM(oi.price) AS metric
FROM order_items oi
JOIN order_payments p ON p.order_id = oi.order_id
