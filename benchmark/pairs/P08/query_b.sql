SELECT COUNT(DISTINCT c.customer_unique_id) AS metric
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id;
