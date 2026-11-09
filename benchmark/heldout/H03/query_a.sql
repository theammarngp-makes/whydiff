SELECT SUM(oi.price) AS metric
FROM order_items oi
WHERE oi.order_id IN (
    SELECT order_id FROM orders WHERE order_status = 'delivered'
)
