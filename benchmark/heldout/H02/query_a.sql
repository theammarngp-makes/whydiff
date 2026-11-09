SELECT SUM(price) AS metric
FROM orders
JOIN order_items ON orders.order_id = order_items.order_id
