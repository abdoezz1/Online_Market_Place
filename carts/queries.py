from core.db.db import execute_query, execute_transaction


def get_cart_items(profile_id):
    sql = """
    SELECT 
        o.id, 
        o.quantity,
        i.name as product_name, 
        i.price, 
        i.image as product_image,
        i.quantity as product_stock,
        u.username as seller_username,
        (i.price * o.quantity) as total_price,
        o.product_id,
        up_seller.id as seller_id
    FROM orders o
    JOIN items i ON o.product_id = i.id
    JOIN user_profiles up_seller ON i.owned_by_id = up_seller.id
    JOIN users u ON up_seller.user_id = u.id
    WHERE o.buyer_id = %s
    """
    return execute_query(sql, (profile_id,), fetch_all=True)


def add_to_cart(profile_id, product_id, qty):
    # check if exists
    sql = "SELECT id, quantity FROM orders WHERE buyer_id=%s AND product_id=%s"
    existing = execute_query(sql, (profile_id, product_id), fetch_one=True)

    if existing:
        sql = "UPDATE orders SET quantity = quantity + %s WHERE id=%s"
        execute_query(sql, (qty, existing["id"]))
    else:
        sql = "INSERT INTO orders (buyer_id, product_id, quantity) VALUES (%s,%s,%s)"
        execute_query(sql, (profile_id, product_id, qty))


def update_cart_item(order_id, qty):
    sql = "UPDATE orders SET quantity=%s WHERE id=%s"
    execute_query(sql, (qty, order_id))


def remove_cart_item(order_id):
    sql = "DELETE FROM orders WHERE id=%s"
    execute_query(sql, (order_id,))

def process_payment_transaction(buyer_id, seller_id, product_id, quantity, total_price, order_id):
    """
    Executes the 7-step atomic payment flow.
    Returns True if successful, False otherwise.
    """
    
    # Inventory logic removed as user_inventory table does not exist in schema.

    # 2. Prepare the Atomic Query List
    # These must be in a specific order to satisfy foreign key constraints 
    # and logical dependencies (like balance checks).
    transaction_steps = [
        # 1. Deduct from buyer
        ("UPDATE user_profiles SET balance = balance - %s WHERE id = %s", 
         (total_price, buyer_id)),
        
        # 2. Add to seller
        ("UPDATE user_profiles SET balance = balance + %s WHERE id = %s", 
         (total_price, seller_id)),
        
        # 3. Record Payment
        ("""INSERT INTO payments 
            (is_successful, buyer_id, seller_id, product_id, quantity, total_price, order_id, payment_date) 
            VALUES (TRUE, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)""", 
         (buyer_id, seller_id, product_id, quantity, total_price, order_id)),
        
        # 4. Record Transaction History
        ("""INSERT INTO transactions (buyer_id, seller_id, product_id, quantity, total_price, status, date) 
            VALUES (%s, %s, %s, %s, %s, 'completed', CURRENT_TIMESTAMP)""", 
         (buyer_id, seller_id, product_id, quantity, total_price)),
        
        # 5. Update Stock (Decrement original item quantity)
        ("UPDATE items SET quantity = quantity - %s WHERE id = %s", 
         (quantity, product_id)),
        
        # 6. Remove item from the orders/cart
        ("DELETE FROM orders WHERE id = %s", 
         (order_id,)),

        # 7. Deliver item to buyer's inventory (Create a non-sale record)
        ("""INSERT INTO items 
            (name, category_id, price, description, image, available_stock, owned_by_id, quantity, for_sale, average_rating)
            SELECT name, category_id, price, description, image, 0, %s, %s, FALSE, average_rating
            FROM items WHERE id = %s""",
         (buyer_id, quantity, product_id))
    ]

    # 3. Execute all 7 steps as one unit
    return execute_transaction(transaction_steps)

def get_order_details(order_id):
    """
    Helper to fetch info from the orders table before processing payment.
    """
    sql = """
        SELECT o.id, o.product_id, o.quantity, i.price, i.owned_by_id as seller_id, o.buyer_id
        FROM orders o
        JOIN items i ON o.product_id = i.id
        WHERE o.id = %s
    """
    return execute_query(sql, (order_id,), fetch_one=True)
