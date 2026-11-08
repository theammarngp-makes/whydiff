SELECT SUM(oi.price) / COUNT(DISTINCT o.order_id) AS metric
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id;
