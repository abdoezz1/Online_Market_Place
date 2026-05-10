from core.db.db import execute_query


def get_item_by_id(item_id):
    return execute_query(
        """SELECT i.*, c.name AS category_name,
                  u.username AS owner_username, up.id AS owner_profile_id
           FROM items i
           JOIN categories c ON i.category_id = c.id
           JOIN user_profiles up ON i.owned_by_id = up.id
           JOIN users u ON up.user_id = u.id
           WHERE i.id = %s""",
        (item_id,), fetch_one=True
    )

def increment_view_count(item_id):
    execute_query(
        "UPDATE items SET view_count = view_count + 1 WHERE id = %s",
        (item_id,)
    )

def get_item_reviews(item_id):
    return execute_query(
        """SELECT r.*, u.username, up.photo
           FROM reviews r
           JOIN user_profiles up ON r.user_id = up.id
           JOIN users u ON up.user_id = u.id
           WHERE r.product_id = %s
           ORDER BY r.created_at DESC""",
        (item_id,), fetch_all=True
    )

def get_items_by_category(category_id):
    return execute_query(
        """SELECT i.*, c.name AS category_name
           FROM items i
           JOIN categories c ON i.category_id = c.id
           WHERE i.category_id = %s AND i.for_sale = TRUE""",
        (category_id,), fetch_all=True
    )

def get_category_by_id(category_id):
    return execute_query(
        "SELECT * FROM categories WHERE id = %s",
        (category_id,), fetch_one=True
    )

def get_home_items(current_profile_id):
    """All for-sale items that don't belong to the current user."""
    return execute_query(
        """SELECT i.*, c.name AS category_name,
                  u.username AS owner_username
           FROM items i
           JOIN categories c ON i.category_id = c.id
           JOIN user_profiles up ON i.owned_by_id = up.id
           JOIN users u ON up.user_id = u.id
           WHERE i.for_sale = TRUE AND i.owned_by_id != %s
           ORDER BY i.created_at DESC""",
        (current_profile_id,), fetch_all=True
    )

def filter_items(current_profile_id, name=None, min_price=None, max_price=None,
                 min_rating=None, category_id=None, sort_by='newest'):
    """
    Dynamic filter query.
    sort_by options: 'newest', 'price_asc', 'price_desc', 'rating'
    """
    conditions = ["i.for_sale = TRUE", "i.owned_by_id != %s"]
    params = [current_profile_id]

    if name:
        conditions.append("(i.name ILIKE %s OR u.username ILIKE %s)")
        params.extend([f"%{name}%", f"%{name}%"])
    if min_price is not None:
        conditions.append("i.price >= %s")
        params.append(min_price)
    if max_price is not None:
        conditions.append("i.price <= %s")
        params.append(max_price)
    if min_rating is not None:
        conditions.append("i.average_rating >= %s")
        params.append(min_rating)
    if category_id:
        conditions.append("i.category_id = %s")
        params.append(category_id)

    order_map = {
        'newest':     'i.created_at DESC',
        'price_asc':  'i.price ASC',
        'price_desc': 'i.price DESC',
        'rating':     'i.average_rating DESC',
    }
    order_clause = order_map.get(sort_by, 'i.created_at DESC')

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT i.*, c.name AS category_name,
               u.username AS owner_username
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN user_profiles up ON i.owned_by_id = up.id
        JOIN users u ON up.user_id = u.id
        WHERE {where_clause}
        ORDER BY {order_clause}
    """
    return execute_query(sql, tuple(params), fetch_all=True)
