SELECT SUM(oi.price) AS metric
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN order_payments p ON p.order_id = o.order_id
WHERE o.order_purchase_timestamp >= TIMESTAMP '2017-11-01 00:00:00'
  AND o.order_purchase_timestamp < TIMESTAMP '2017-12-01 00:00:00';
