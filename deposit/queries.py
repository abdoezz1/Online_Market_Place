from core.db.db import execute_query, execute_transaction
import uuid

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

def create_deposit_and_update_balance(profile_id, amount):
    """Executes the deposit and balance update in a single transaction."""
    # 1. Fetch a new ID from the transactions sequence to satisfy the foreign key
    res = execute_query("SELECT nextval('transactions_transaction_id_seq') as tid", fetch_one=True)
    if not res:
        return False
    t_id = res['tid']
    
    # 2. Step 1: Create the parent record in the transactions table
    # This is required because deposits.transaction_id is a foreign key to transactions.transaction_id
    t_sql = """
        INSERT INTO transactions (transaction_id, buyer_id, quantity, total_price, status, date)
        VALUES (%s, %s, 1, %s, 'deposit', CURRENT_TIMESTAMP)
    """
    t_params = (t_id, profile_id, amount)

    # 3. Step 2: Create the deposit record
    d_sql, d_params = create_deposit_query(amount, "completed", t_id, profile_id)
    
    # 4. Step 3: Update the user balance
    b_sql, b_params = update_balance_query(profile_id, amount)
    
    return execute_transaction([
        (t_sql, t_params),
        (d_sql, d_params),
        (b_sql, b_params)
    ])

def get_deposit_by_id(deposit_id, profile_id):
    """Fetches a specific deposit record for receipt printing."""
    sql = "SELECT * FROM deposits WHERE id = %s AND user_id = %s"
    return execute_query(sql, (deposit_id, profile_id), fetch_one=True)
