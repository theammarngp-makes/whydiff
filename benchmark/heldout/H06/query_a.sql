SELECT SUM(oi.price) AS metric
FROM orders ord
JOIN order_items oi ON oi.order_id = ord.order_id
WHERE ord.order_purchase_timestamp BETWEEN '2017-11-01' AND '2017-11-30'
