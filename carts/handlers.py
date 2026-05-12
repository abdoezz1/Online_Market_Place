from template_engine import render_template
from core.http.response_builder import build_response, redirect, error_response
from core.auth.session_manager import require_login
import core.queries as core_queries
from carts import queries


@require_login
def view_cart(request):
    profile_id = request["profile_id"]

    items = queries.get_cart_items(profile_id)
    
    orders = []
    for item in items:
        orders.append({
            "id": item["id"],
            "quantity": item["quantity"],
            "total_price": item["total_price"],
            "product": {
                "name": item["product_name"],
                "price": item["price"],
                "image": item["product_image"],
                "quantity": item["product_stock"]
            },
            "seller": {
                "user": item["seller_username"]
            },
            "buyer": {
                "user": request["user"]
            }
        })

    total_price = sum(item["total_price"] for item in items)

    html = render_template("carts/cart.html", {
        "orders": orders,
        "total_price": total_price,
        "user": request.get("user")
    })
    return build_response(200, html)


@require_login
def add_to_cart(request):
    profile_id = request["profile_id"]
    product_id = request["query_params"].get("product_id")
    qty = int(request["query_params"].get("quantity", 1))

    queries.add_to_cart(profile_id, product_id, qty)
    return redirect("/home/cart")


@require_login
def edit_order(request):
    order_id = request["path_params"]["id"]
    qty = int(request["form_data"].get("quantity"))

    queries.update_cart_item(order_id, qty)
    return redirect("/home/cart")


@require_login
def remove_order(request):
    order_id = request["path_params"]["id"]

    queries.remove_cart_item(order_id)
    return redirect("/home/cart")


@require_login
def process_payment(request):
    profile_id = request["profile_id"]
    
    # 1. Fetch current balance
    profile = core_queries.get_user_profile_by_pk(profile_id)
    if not profile:
        return error_response(404, "User profile not found")
    
    balance = profile["balance"]
    
    # 2. Fetch all cart items
    cart_items = queries.get_cart_items(profile_id)
    if not cart_items:
        return redirect("/home/cart") # Nothing to pay for
    
    total_cart_price = sum(item["total_price"] for item in cart_items)
    
    # 3. Check balance
    if balance < total_cart_price:
        # In a real app, we'd use a flash message, but here we'll just redirect with an error param
        # or render the cart with an error. 
        # For now, let's redirect back to cart.
        return redirect("/home/cart?error=insufficient_balance")

    # 4. Process each item atomically
    for item in cart_items:
        queries.process_payment_transaction(
            buyer_id=profile_id,
            seller_id=item["seller_id"],
            product_id=item["product_id"],
            quantity=item["quantity"],
            total_price=item["total_price"],
            order_id=item["id"]
        )
            
    return redirect("/dashboard")
