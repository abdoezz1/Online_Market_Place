from core.db.db import execute_query

def get_daily_deposit_count(profile_id):
    """Checks how many deposits the user has made today."""
    sql = "SELECT COUNT(*) as count FROM deposits WHERE user_id = %s AND date::date = CURRENT_DATE"
    result = execute_query(sql, (profile_id,), fetch_one=True)
    return result['count'] if result else 0

def create_deposit_query(amount, status, transaction_id, profile_id):
    """Returns the SQL and params for creating a deposit record."""
    sql = "INSERT INTO deposits (amount, status, transaction_id, user_id) VALUES (%s, %s, %s, %s)"
    params = (amount, status, transaction_id, profile_id)
    return sql, params

def update_balance_query(profile_id, amount):
    """Returns the SQL and params for increasing user balance."""
    sql = "UPDATE user_profiles SET balance = balance + %s WHERE id = %s"
    params = (amount, profile_id)
    return sql, params

def get_deposit_by_id(deposit_id, profile_id):
    """Fetches a specific deposit record for receipt printing."""
    sql = "SELECT * FROM deposits WHERE id = %s AND user_id = %s"
    return execute_query(sql, (deposit_id, profile_id), fetch_one=True)
