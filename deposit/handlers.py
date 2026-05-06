from datetime import datetime
from template_engine import render_template
from response_builder import build_response, redirect, error_response
from session_manager import require_login, get_current_user
from deposit import queries as deposit_queries

@require_login
def deposit_page(request):
    """GET /deposit - Renders the deposit form"""
    # Get current user to show current balance in the navbar/page
    user_id = get_current_user(request)
    return build_response(200, render_template("deposit/deposit.html", {"user_id": user_id}))

@require_login
def process_deposit(request):
    """POST /deposit/process - Validates and saves a deposit"""
    if request['method'] != 'POST':
        return error_response(405, "Method Not Allowed")

    user_id = get_current_user(request)
    data = request.get('form_data', {})
    
    # **Extract and Clean Data**
    card_number = data.get('card_number', '').strip()
    cvv = data.get('cvv', '').strip()
    exp_month = data.get('expiration_month', '')
    exp_year = data.get('expiration_year', '')
  
    try:
        amount = float(data.get('amount', 0))
    except ValueError:
        return error_response(400, "Invalid amount format")

    # **Validation Rules**
    # Card exactly 16 digits, starts with 4 or 5
    if not (len(card_number) == 16 and card_number[0] in ('4', '5')):
        return error_response(400, "Invalid card: Must be 16 digits starting with 4 or 5")
    
    # CVV exactly 3 digits
    if not (len(cvv) == 3 and cvv.isdigit()):
        return error_response(400, "Invalid CVV: Must be 3 digits")
    
    # Amount between 10 and 10,000
    if not (10 <= amount <= 10000):
        return error_response(400, "Amount must be between 10 and 10,000")

    # Max 3 deposits per day per user
    daily_count = deposit_queries.get_daily_deposit_count(user_id)
    if daily_count >= 3:
        return error_response(403, "Deposit limit reached: Max 3 per day")

    # Expiry Check
    try:
        # Create a date object for the first day of the expiration month
        expiry_date = datetime.strptime(f"{exp_month}/{exp_year}", "%m/%Y")
        
        # If the current date is past that month, reject the transaction
        if expiry_date < datetime.now():
            return error_response(400, "Card is expired.")
            
    except ValueError:
        # This triggers if the month/year format is incorrect (e.g., month "13")
        return error_response(400, "Invalid expiration date format (MM/YYYY).")

    # **Save to Database and update user balance**
    success = deposit_queries.create_deposit_and_update_balance(user_id, amount)
    
    if success:
        return redirect("/dashboard/transaction-report")
    else:
        return error_response(500, "Transaction failed. Please try again.")
