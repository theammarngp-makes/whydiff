SELECT SUM(order_items.price) AS metric
FROM orders
JOIN order_items ON orders.order_id = order_items.order_id
WHERE orders.order_status = 'delivered'
