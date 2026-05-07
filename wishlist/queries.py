from db import execute_query


def get_wishlist(user_id):
    sql = """
    SELECT i.*
    FROM wishlist w
    JOIN items i ON w.product_id = i.id
    WHERE w.user_id = %s
    """
    return execute_query(sql, (user_id,), fetch_all=True)


def toggle_wishlist(user_id, product_id):
    sql = "SELECT * FROM wishlist WHERE user_id=%s AND product_id=%s"
    exists = execute_query(sql, (user_id, product_id), fetch_one=True)

    if exists:
        sql = "DELETE FROM wishlist WHERE user_id=%s AND product_id=%s"
        execute_query(sql, (user_id, product_id))
    else:
        sql = "INSERT INTO wishlist (user_id, product_id) VALUES (%s,%s)"
        execute_query(sql, (user_id, product_id))
