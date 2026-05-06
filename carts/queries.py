from db import execute_query, execute_transaction


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

def check_user_item_ownership(user_id, product_id):
    """
    Checks if the buyer already owns at least one copy of this product.
    Used to decide between INSERT or UPDATE for the inventory step.
    """
    sql = "SELECT quantity FROM user_inventory WHERE user_id = %s AND item_id = %s"
    return execute_query(sql, (user_id, product_id), fetch_one=True)

def process_payment_transaction(buyer_id, seller_id, product_id, quantity, total_price, order_id):
    """
    Executes the 7-step atomic payment flow.
    Returns True if successful, False otherwise.
    """
    
    # 1. Determine if we need to INSERT or UPDATE the buyer's inventory
    ownership = check_user_item_ownership(buyer_id, product_id)
    
    if ownership:
        # Update existing ownership
        inventory_sql = "UPDATE user_inventory SET quantity = quantity + %s WHERE user_id = %s AND item_id = %s"
        inventory_params = (quantity, buyer_id, product_id)
    else:
        # Create new ownership record
        inventory_sql = "INSERT INTO user_inventory (user_id, item_id, quantity) VALUES (%s, %s, %s)"
        inventory_params = (buyer_id, product_id, quantity)

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
        
        # 3. Handle Inventory (calculated above)
        (inventory_sql, inventory_params),
        
        # 4. Record Payment
        ("INSERT INTO payments (amount, user_id, date) VALUES (%s, %s, CURRENT_TIMESTAMP)", 
         (total_price, buyer_id)),
        
        # 5. Record Transaction History
        ("""INSERT INTO transactions (buyer_id, seller_id, product_id, quantity, total_price, status, date) 
            VALUES (%s, %s, %s, %s, %s, 'transaction', CURRENT_TIMESTAMP)""", 
         (buyer_id, seller_id, product_id, quantity, total_price)),
        
        # 6. Update Stock (Decrement original item quantity)
        ("UPDATE items SET quantity = quantity - %s WHERE id = %s", 
         (quantity, product_id)),
        
        # 7. Remove item from the orders/cart
        ("DELETE FROM orders WHERE id = %s", 
         (order_id,))
    ]

    # 3. Execute all 7 steps as one unit
    return execute_transaction(transaction_steps)

def get_order_details(order_id):
    """
    Helper to fetch info from the orders table before processing payment.
    """
    sql = """
        SELECT o.id, o.product_id, o.quantity, i.price, i.owner_id as seller_id
        FROM orders o
        JOIN items i ON o.product_id = i.id
        WHERE o.id = %s
    """
    return execute_query(sql, (order_id,), fetch_one=True)
