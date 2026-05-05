from template_engine import render_template
from response_builder import build_response, redirect
from session_manager import require_login
from carts import queries


@require_login
def view_cart(request):
    user_id = request["user_id"]

    items = queries.get_cart_items(user_id)
    total = sum(item["price"] * item["quantity"] for item in items)

    html = render_template("carts/cart.html", {
        "items": items,
        "total": total,
        "user": request.get("user")
    })
    return build_response(200, html)


@require_login
def add_to_cart(request):
    user_id = request["user_id"]
    product_id = request["query_params"].get("product_id")
    qty = int(request["query_params"].get("qty", 1))

    queries.add_to_cart(user_id, product_id, qty)
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
