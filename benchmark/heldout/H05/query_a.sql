-- Finance view: revenue of reviewed orders
SELECT SUM(items.price) AS metric
FROM orders AS ord
	JOIN order_reviews AS rev ON rev.order_id = ord.order_id
	JOIN order_items AS items ON ord.order_id = items.order_id
