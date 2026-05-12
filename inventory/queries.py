"""
inventory/queries.py — Raw SQL Queries for Inventory Module
=============================================================

Every database interaction for the inventory feature lives here.
Handlers never write SQL directly — they call these functions instead.

All functions use `db.execute_query()` from core.db for connection pooling
and parameterised queries (prevents SQL injection).
"""

from core.db import db


# ─────────────────────────────────────────────────────────────────────────────
#  Item Queries
# ─────────────────────────────────────────────────────────────────────────────

def get_items_by_owner(user_id):
    """
    Fetch all items belonging to a user, ordered by newest first.
    Joins with categories to include the category name.

    Returns: list of dicts (may be empty)
    """
    return db.execute_query(
        """
        SELECT i.id, i.name, i.price, i.description, i.image,
               i.available_stock, i.quantity, i.for_sale, i.advertise,
               i.quantity_advertise, i.average_rating, i.created_at,
               c.id AS category_id, c.name AS category_name
        FROM items i
        JOIN categories c ON i.category_id = c.id
        WHERE i.owned_by_id = (
            SELECT id FROM user_profiles WHERE user_id = %s
        )
        ORDER BY i.created_at DESC
        """,
        (user_id,),
        fetch_all=True
    )


def get_item_by_id(item_id):
    """
    Fetch a single item by its primary key.
    Includes the category name and owner info.

    Returns: dict or None
    """
    return db.execute_query(
        """
        SELECT i.id, i.name, i.price, i.description, i.image,
               i.available_stock, i.quantity, i.for_sale, i.advertise,
               i.quantity_advertise, i.average_rating, i.created_at,
               c.id AS category_id, c.name AS category_name,
               up.id AS profile_id, up.user_id AS owner_user_id
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN user_profiles up ON i.owned_by_id = up.id
        WHERE i.id = %s
        LIMIT 1
        """,
        (item_id,),
        fetch_one=True
    )


def insert_item(name, category_id, price, description, image_path,
                quantity, for_sale, advertise, quantity_advertise, user_id):
    """
    Insert a new item into the database.
    Looks up the user's profile_id from the user_id.
    available_stock is auto-set based on quantity > 0.

    Returns: dict with the new item's 'id', or None on failure
    """
    available_stock = 1 if quantity > 0 else 0
    return db.execute_query(
        """
        INSERT INTO items
            (name, category_id, price, description, image,
             available_stock, owned_by_id, created_at, quantity,
             for_sale, average_rating, advertise, quantity_advertise)
        VALUES
            (%s, %s, %s, %s, %s,
             %s, (SELECT id FROM user_profiles WHERE user_id = %s),
             CURRENT_TIMESTAMP, %s,
             %s, 0.00, %s, %s)
        RETURNING id
        """,
        (name, category_id, price, description, image_path,
         available_stock, user_id, quantity,
         for_sale, advertise, quantity_advertise),
        fetch_one=True
    )


def update_item(item_id, name, category_id, price, description,
                image_path, quantity, for_sale, advertise, quantity_advertise):
    """
    Update an existing item's fields.
    If image_path is None, the image column is left unchanged.

    Returns: dict with the updated item's 'id', or None
    """
    available_stock = 1 if quantity > 0 else 0

    if image_path is not None:
        return db.execute_query(
            """
            UPDATE items
            SET name = %s, category_id = %s, price = %s, description = %s,
                image = %s, quantity = %s, available_stock = %s,
                for_sale = %s, advertise = %s, quantity_advertise = %s
            WHERE id = %s
            RETURNING id
            """,
            (name, category_id, price, description,
             image_path, quantity, available_stock,
             for_sale, advertise, quantity_advertise,
             item_id),
            fetch_one=True
        )
    else:
        return db.execute_query(
            """
            UPDATE items
            SET name = %s, category_id = %s, price = %s, description = %s,
                quantity = %s, available_stock = %s,
                for_sale = %s, advertise = %s, quantity_advertise = %s
            WHERE id = %s
            RETURNING id
            """,
            (name, category_id, price, description,
             quantity, available_stock,
             for_sale, advertise, quantity_advertise,
             item_id),
            fetch_one=True
        )


def delete_item_by_id(item_id):
    """
    Delete an item by its primary key.

    Returns: dict with deleted item's 'id', or None if not found
    """
    return db.execute_query(
        "DELETE FROM items WHERE id = %s RETURNING id",
        (item_id,),
        fetch_one=True
    )


def get_item_owner_user_id(item_id):
    """
    Get the user_id (auth user) of the item's owner.
    Used for permission checks.

    Returns: int (user_id) or None
    """
    row = db.execute_query(
        """
        SELECT up.user_id
        FROM items i
        JOIN user_profiles up ON i.owned_by_id = up.id
        WHERE i.id = %s
        LIMIT 1
        """,
        (item_id,),
        fetch_one=True
    )
    return row["user_id"] if row else None


def bulk_insert_items(rows, user_id):
    """
    Insert multiple items at once (used by CSV upload).

    Args:
        rows: list of dicts, each with keys:
              name, category_id, price, description, quantity
        user_id: the logged-in user's id

    Returns: int — number of rows inserted
    """
    count = 0
    for row in rows:
        result = insert_item(
            name=row["name"],
            category_id=row["category_id"],
            price=row["price"],
            description=row.get("description", ""),
            image_path=row.get("image", "default-product-image.jpg"),
            quantity=row.get("quantity", 1),
            for_sale=True,
            advertise=False,
            quantity_advertise=0,
            user_id=user_id
        )
        if result:
            count += 1
    return count


# ─────────────────────────────────────────────────────────────────────────────
#  Category Queries
# ─────────────────────────────────────────────────────────────────────────────

def get_all_categories():
    """
    Fetch all categories ordered by name.

    Returns: list of dicts
    """
    return db.execute_query(
        "SELECT id, name FROM categories ORDER BY name",
        fetch_all=True
    )


def get_or_create_category(name):
    """
    Return the category with the given name, creating it if it doesn't exist.

    Returns: (dict, bool) — (category row, was_created)
    """
    existing = db.execute_query(
        "SELECT id, name FROM categories WHERE LOWER(name) = LOWER(%s) LIMIT 1",
        (name.strip(),),
        fetch_one=True
    )
    if existing:
        return existing, False

    new_cat = db.execute_query(
        "INSERT INTO categories (name) VALUES (%s) RETURNING id, name",
        (name.strip(),),
        fetch_one=True
    )
    return new_cat, True


def get_category_by_id(category_id):
    """
    Fetch a single category by id.

    Returns: dict or None
    """
    return db.execute_query(
        "SELECT id, name FROM categories WHERE id = %s LIMIT 1",
        (category_id,),
        fetch_one=True
    )


def get_category_by_name(name):
    """
    Fetch a single category by name (case-insensitive).

    Returns: dict or None
    """
    return db.execute_query(
        "SELECT id, name FROM categories WHERE LOWER(name) = LOWER(%s) LIMIT 1",
        (name.strip(),),
        fetch_one=True
    )


def count_items_in_category(category_id):
    """
    Count how many items reference this category.

    Returns: int
    """
    row = db.execute_query(
        "SELECT COUNT(*) AS cnt FROM items WHERE category_id = %s",
        (category_id,),
        fetch_one=True
    )
    return row["cnt"] if row else 0


def delete_category_by_id(category_id):
    """
    Delete a category by its primary key.

    Returns: dict with deleted category's 'id', or None
    """
    return db.execute_query(
        "DELETE FROM categories WHERE id = %s RETURNING id, name",
        (category_id,),
        fetch_one=True
    )

