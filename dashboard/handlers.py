from . import queries as dashboard_queries

from core.db.db import execute_transaction
from core.auth.session_manager import require_login, get_current_user
from template_engine import render_template
from core.http.response_builder import build_response, error_response, json_response

from deposit.queries import get_deposit_by_id


# ─────────────────────────────────────────────
# TRANSACTION REPORT
# ─────────────────────────────────────────────

@require_login
def transaction_report(request):
    user_id = request.get("user_id")
    user = request.get("user") or {}
    profile_id = request.get("profile_id")

    if user.get("is_staff"):
        transactions = dashboard_queries.get_all_transactions() or []
        deposits = dashboard_queries.get_all_deposits() or []
    else:
        transactions = dashboard_queries.get_user_transactions(profile_id) or []
        deposits = dashboard_queries.get_user_deposits(profile_id) or []

    combined_data = []

    for t in transactions:
        combined_data.append({
            "type": "Transaction",
            "data": t,
            "date": t["date"]
        })

    for d in deposits:
        combined_data.append({
            "type": "Deposit",
            "data": d,
            "date": d["date"]
        })

    combined_data.sort(key=lambda x: x["date"], reverse=True)

    html = render_template("dashboard/transaction_report.html", {
        "combined_data": combined_data,
        "user": user,
        "profile": request.get("profile"),
        "user_profile": user.get("username", "User")
    })

    return build_response(200, html, "text/html")


# ─────────────────────────────────────────────
# PRINT TRANSACTION
# ─────────────────────────────────────────────

@require_login
def print_transaction(request):
    t_id = request.get("path_params", {}).get("id")

    transaction = dashboard_queries.get_transaction_by_id(t_id)

    if not transaction:
        return error_response(404, "Transaction not found")

    html = render_template("dashboard/print_transaction.html", {
        "transaction": transaction,
        "user": request.get("user")
    })

    return build_response(200, html, "text/html")


# ─────────────────────────────────────────────
# PRINT DEPOSIT
# ─────────────────────────────────────────────

@require_login
def print_deposit(request):
    d_id = request.get("path_params", {}).get("id")
    user = request.get("user") or {}

    deposit = get_deposit_by_id(d_id, user.get("profile_id"))

    if not deposit:
        return error_response(404, "Deposit not found")

    html = render_template("dashboard/print_deposit.html", {
        "deposit": deposit,
        "user": user
    })

    return build_response(200, html, "text/html")


# ─────────────────────────────────────────────
# MAKE REVIEW PAGE
# ─────────────────────────────────────────────

@require_login
def make_review_page(request):
    profile_id = request.get("profile_id")
    transaction_id = request["path_params"].get("id")

    transaction = dashboard_queries.get_transaction_by_id(transaction_id)

    if not transaction or transaction["buyer_id"] != profile_id:
        return error_response(403, "You can only review your own purchases.")

    return build_response(
        200,
        render_template("dashboard/make_review.html", {
            "transaction": transaction
        }),
        "text/html"
    )


# ─────────────────────────────────────────────
# SUBMIT REVIEW
# ─────────────────────────────────────────────

@require_login
def make_review_submit(request):
    user_profile_id = request.get("profile_id")
    t_id = request.get("path_params", {}).get("id")
    data = request.get("form_data", {})

    transaction = dashboard_queries.get_transaction_by_id(t_id)

    if not transaction:
        return error_response(404, "Transaction not found")

    product_id = transaction["product_id"]
    rating = data.get("rating")
    comment = data.get("comment", "")

    if not rating:
        return error_response(400, "Please select a rating.")

    if dashboard_queries.check_review_exists(user_profile_id, t_id, product_id):
        return error_response(400, "Review already submitted.")

    q1_sql, q1_params = dashboard_queries.create_review(
        t_id, user_profile_id, product_id, rating, comment
    )
    q2_sql, q2_params = dashboard_queries.update_product_rating_query(product_id)

    success = execute_transaction([
        (q1_sql, q1_params),
        (q2_sql, q2_params)
    ])

    if success:
        from core.http.response_builder import redirect
        return redirect("/dashboard")

    return error_response(500, "Failed to save review.")


# ─────────────────────────────────────────────
# DASHBOARD HOME
# ─────────────────────────────────────────────

@require_login
def dashboard_home(request):
    user = request.get("user") or {}

    html = render_template("dashboard/dashboard.html", {
        "user": user
    })

    return build_response(200, html, "text/html")