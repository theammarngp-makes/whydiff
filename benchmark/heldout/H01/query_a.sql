select sum(order_items.price) as metric
from orders
join order_items on orders.order_id = order_items.order_id
