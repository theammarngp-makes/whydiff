WITH d AS (
  SELECT order_id FROM orders WHERE order_status = 'delivered'
)
SELECT SUM(oi.price) AS metric
FROM order_items oi
JOIN d ON d.order_id = oi.order_id;
