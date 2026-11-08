SELECT SUM(oi.price + oi.freight_value) AS metric
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered';
