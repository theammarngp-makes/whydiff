SELECT SUM(oi.price) AS metric
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
LEFT JOIN order_payments p ON p.order_id = o.order_id;
