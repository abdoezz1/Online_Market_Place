from core.db.db import execute_query

# --- TRANSACTIONS ---

def get_all_transactions():
    """Fetches all transactions with joined names for admin view."""
    sql = """
        SELECT t.*, u_buyer.username as buyer_name, u_seller.username as seller_name,
               i.name as product_name
        FROM transactions t
        LEFT JOIN user_profiles up_b ON t.buyer_id = up_b.id
        LEFT JOIN users u_buyer ON up_b.user_id = u_buyer.id
        LEFT JOIN user_profiles up_s ON t.seller_id = up_s.id
        LEFT JOIN users u_seller ON up_s.user_id = u_seller.id
        LEFT JOIN items i ON t.product_id = i.id
        ORDER BY t.date DESC
    """
    return execute_query(sql, fetch_all=True)

def get_user_transactions(profile_id):
    """Fetches transactions where the user is either the buyer or the seller."""
    sql = """
        SELECT t.*, u_buyer.username as buyer_name, u_seller.username as seller_name,
               i.name as product_name
        FROM transactions t
        LEFT JOIN user_profiles up_b ON t.buyer_id = up_b.id
        LEFT JOIN users u_buyer ON up_b.user_id = u_buyer.id
        LEFT JOIN user_profiles up_s ON t.seller_id = up_s.id
        LEFT JOIN users u_seller ON up_s.user_id = u_seller.id
        LEFT JOIN items i ON t.product_id = i.id
        WHERE t.buyer_id = %s OR t.seller_id = %s
        ORDER BY t.date DESC
    """
    return execute_query(sql, (profile_id, profile_id), fetch_all=True)

def get_transaction_by_id(transaction_id):
    """Fetches a single transaction by its primary key."""
    sql = """
        SELECT t.*, 
               u_buyer.username as buyer, 
               u_seller.username as seller,
               i.name as product_name,
               i.price as product_price
        FROM transactions t
        LEFT JOIN user_profiles up_b ON t.buyer_id = up_b.id
        LEFT JOIN users u_buyer ON up_b.user_id = u_buyer.id
        LEFT JOIN user_profiles up_s ON t.seller_id = up_s.id
        LEFT JOIN users u_seller ON up_s.user_id = u_seller.id
        LEFT JOIN items i ON t.product_id = i.id
        WHERE t.transaction_id = %s
    """
    return execute_query(sql, (transaction_id,), fetch_one=True)

# --- DEPOSITS ---

def get_all_deposits():
    """Fetches all deposits with usernames for admin view."""
    sql = """
        SELECT d.*, u.username 
        FROM deposits d
        JOIN user_profiles up ON d.user_id = up.id
        JOIN users u ON up.user_id = u.id
        ORDER BY d.date DESC
    """
    return execute_query(sql, fetch_all=True)

def get_user_deposits(profile_id):
    """Fetches all deposits made by a specific user."""
    sql = "SELECT * FROM deposits WHERE user_id = %s ORDER BY date DESC"
    return execute_query(sql, (profile_id,), fetch_all=True)

# --- REVIEWS ---

def check_review_exists(user_profile_id, transaction_id, product_id):
    """Validates if a user has already reviewed a specific product for a transaction."""
    sql = "SELECT COUNT(*) as count FROM reviews WHERE user_id = %s AND transaction_id = %s AND product_id = %s"
    result = execute_query(sql, (user_profile_id, transaction_id, product_id), fetch_one=True)
    return result['count'] > 0 if result else False

def create_review(transaction_id, user_profile_id, product_id, rating, comment):
    """Inserts a new review record."""
    sql = "INSERT INTO reviews (transaction_id, user_id, product_id, rating, comment) VALUES (%s, %s, %s, %s, %s)"
    return sql, (transaction_id, user_profile_id, product_id, rating, comment)

def update_product_rating_query(product_id):
    """Calculates and updates the average rating for a product."""
    sql = """
        UPDATE items 
        SET average_rating = (SELECT AVG(rating) FROM reviews WHERE product_id = %s)
        WHERE id = %s
    """
    return sql, (product_id, product_id)
