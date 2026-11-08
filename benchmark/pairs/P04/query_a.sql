SELECT SUM(p.payment_value) AS metric
FROM orders o
JOIN order_payments p ON p.order_id = o.order_id;
