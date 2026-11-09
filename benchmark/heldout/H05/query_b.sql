SELECT SUM(i.price) AS metric
FROM orders AS o
JOIN order_items AS i
  ON o.order_id = i.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
