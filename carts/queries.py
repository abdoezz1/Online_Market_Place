from db import execute_query


def get_cart_items(user_id):
    sql = """
    SELECT o.id, i.name, i.price, o.quantity
    FROM orders o
    JOIN items i ON o.product_id = i.id
    WHERE o.user_id = %s
    """
    return execute_query(sql, (user_id,), fetch_all=True)


def add_to_cart(user_id, product_id, qty):
    # check if exists
    sql = "SELECT id, quantity FROM orders WHERE user_id=%s AND product_id=%s"
    existing = execute_query(sql, (user_id, product_id), fetch_one=True)

    if existing:
        sql = "UPDATE orders SET quantity = quantity + %s WHERE id=%s"
        execute_query(sql, (qty, existing["id"]))
    else:
        sql = "INSERT INTO orders (user_id, product_id, quantity) VALUES (%s,%s,%s)"
        execute_query(sql, (user_id, product_id, qty))


def update_cart_item(order_id, qty):
    sql = "UPDATE orders SET quantity=%s WHERE id=%s"
    execute_query(sql, (qty, order_id))


def remove_cart_item(order_id):
    sql = "DELETE FROM orders WHERE id=%s"
    execute_query(sql, (order_id,))
