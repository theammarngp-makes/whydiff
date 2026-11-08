SELECT SUM(oi.price) AS metric
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN order_reviews r ON r.order_id = o.order_id;
