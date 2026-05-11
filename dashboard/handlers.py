from . import queries
from core.db.db import execute_transaction
from core.auth.session_manager import require_login
from template_engine import render_template
from core.http.response_builder import build_response, error_response, json_response
from deposit.queries import get_deposit_by_id


@require_login
def transaction_report(request):
    print("USER DEBUG:", request.get('user'))
    
    user = request.get('user') or {}
    profile_id = user.get('profile_id')

    if user.get('is_staff'):
        transactions = queries.get_all_transactions() or []
        deposits = queries.get_all_deposits() or []  
    else:
        transactions = queries.get_user_transactions(profile_id) or []
        deposits = queries.get_user_deposits(profile_id) or []

    combined_data = []

    for t in transactions:
        combined_data.append({'type': 'Transaction', 'data': t, 'date': t['date']})

    for d in deposits:
        combined_data.append({'type': 'Deposit', 'data': d, 'date': d['date']})

    combined_data.sort(key=lambda x: x['date'], reverse=True)

    html = render_template('dashboard/transaction_report.html', {
        'activities': combined_data,
        'user': user
    })

    return build_response(200, html, 'text/html')

@require_login
def print_transaction(request):
    t_id = request.get('path_params', {}).get('id')
    transaction = queries.get_transaction_by_id(t_id)

    if not transaction:
        return error_response(404, "Transaction not found")

    html = render_template('dashboard/print_transaction.html', {
        'transaction': transaction,
        'user': request.get('user')
    })

    return build_response(200, html, 'text/html')


@require_login
def print_deposit(request):
    d_id = request.get('path_params', {}).get('id')
    user = request.get('user') or {}

    deposit = get_deposit_by_id(d_id, user.get('profile_id'))

    if not deposit:
        return error_response(404, "Deposit not found")

    html = render_template('dashboard/print_deposit.html', {
        'deposit': deposit,
        'user': user
    })

    return build_response(200, html, 'text/html')


@require_login
def make_review_page(request):
    t_id = request.get('path_params', {}).get('id')
    transaction = queries.get_transaction_by_id(t_id)

    if not transaction:
        return error_response(404, "Transaction not found")

    html = render_template('dashboard/make_review.html', {
        'transaction': transaction,
        'user': request.get('user')
    })

    return build_response(200, html, 'text/html')


@require_login
def make_review_submit(request):
    user_profile_id = request.get('user').get('profile_id')
    t_id = request.get('path_params', {}).get('id')
    data = request.get('form_data', {})

    transaction = queries.get_transaction_by_id(t_id)

    if not transaction:
        return error_response(404, "Transaction not found")

    product_id = transaction['product_id']
    rating = data.get('rating')
    comment = data.get('comment', '')

    if queries.check_review_exists(user_profile_id, t_id, product_id):
        return error_response(400, "Review already submitted.")

    q1_sql, q1_params = queries.create_review(
        t_id, user_profile_id, product_id, rating, comment
    )
    q2_sql, q2_params = queries.update_product_rating_query(product_id)

    success = execute_transaction([
        (q1_sql, q1_params),
        (q2_sql, q2_params)
    ])

    if success:
        return json_response({"message": "Review submitted successfully!"}, 201)

    return error_response(500, "Failed to save review.")


@require_login
def dashboard_home(request):
    user = request.get('user') or {}

    html = render_template('dashboard/dashboard.html', {
        'user': user
    })

    return build_response(200, html, 'text/html')


# from . import queries
# from core.db.db import execute_transaction
# from core.auth.session_manager import require_login
# from template_engine import render_template
# from core.http.response_builder import build_response, error_response, json_response

# @require_login
# def transaction_report(request):
#     """
#     Combines transactions and deposits into a single sorted list.
#     Staff members see all records, while regular users see only their own.
#     """
#     user = request.get('user')
#     profile_id = user.get('profile_id')
    
#     if user.get('is_staff'):
#         transactions = queries.get_all_transactions()
#         deposits = queries.get_all_deposits()
#     else:
#         transactions = queries.get_user_transactions(profile_id)
#         deposits = queries.get_user_deposits(profile_id)

#     # Label data types to distinguish them in the template
#     combined_data = []
#     for t in transactions:
#         combined_data.append({'type': 'Transaction', 'data': t, 'date': t['date']})
#     for d in deposits:
#         combined_data.append({'type': 'Deposit', 'data': d, 'date': d['date']})

#     # Sort combined list by date descending
#     combined_data.sort(key=lambda x: x['date'], reverse=True)

#     html = render_template('dashboard/transaction_report.html', activities=combined_data)
#     return build_response(200, html, 'text/html')

# @require_login
# def print_transaction(request):
#     """Renders a receipt for a specific transaction."""
#     t_id = request.get('path_params', {}).get('id')
#     transaction = queries.get_transaction_by_id(t_id)
    
#     if not transaction:
#         return error_response(404, "Transaction not found")
        
#     html = render_template('dashboard/print_transaction.html', transaction=transaction)
#     return build_response(200, html, 'text/html')

# @require_login
# def print_deposit(request):
#     """Renders a receipt for a specific deposit."""
#     # Importing from deposit module as per cross-app logic
#     from deposit.queries import get_deposit_by_id
#     d_id = request.get('path_params', {}).get('id')
#     deposit = get_deposit_by_id(d_id, request.get('user').get('profile_id'))
    
#     if not deposit:
#         return error_response(404, "Deposit not found")
        
#     html = render_template('dashboard/print_deposit.html', deposit=deposit)
#     return build_response(200, html, 'text/html')

# @require_login
# def make_review_page(request):
#     """Displays the review submission form."""
#     t_id = request.get('path_params', {}).get('id')
#     transaction = queries.get_transaction_by_id(t_id)
    
#     if not transaction:
#         return error_response(404, "Transaction not found")
        
#     html = render_template('dashboard/make_review.html', transaction=transaction)
#     return build_response(200, html, 'text/html')

# @require_login
# def make_review_submit(request):
#     """
#     Handles review submission.
#     Validates that only one review exists per transaction/product/user.
#     Recalculates product rating atomically.
#     """
#     user_profile_id = request.get('user').get('profile_id')
#     t_id = request.get('path_params', {}).get('id')
#     data = request.get('form_data', {})
    
#     transaction = queries.get_transaction_by_id(t_id)
#     if not transaction:
#         return error_response(404, "Transaction not found")
        
#     product_id = transaction['product_id']
#     rating = data.get('rating')
#     comment = data.get('comment', '')

#     # Validation logic
#     if queries.check_review_exists(user_profile_id, t_id, product_id):
#         return error_response(400, "Review already submitted for this transaction.")

#     # Prepare queries for atomic transaction
#     q1_sql, q1_params = queries.create_review(t_id, user_profile_id, product_id, rating, comment)
#     q2_sql, q2_params = queries.update_product_rating_query(product_id)
    
#     success = execute_transaction([
#         (q1_sql, q1_params),
#         (q2_sql, q2_params)
#     ])

#     if success:
#         return json_response({"message": "Review submitted successfully!"}, 201)
    
#     return error_response(500, "Failed to save review.")

# @require_login
# def dashboard_home(request):
#     user = request.get('user')

#     html = render_template('dashboard/dashboard.html', {
#         'user': user
#     })

#     return build_response(200, html, 'text/html') 
