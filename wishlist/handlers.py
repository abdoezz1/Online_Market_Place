from template_engine import render_template
from response_builder import build_response, redirect
from session_manager import require_login
from wishlist import queries


@require_login
def view_wishlist(request):
    user_id = request["user_id"]
    items = queries.get_wishlist(user_id)

    html = render_template("wishlist/wishlist.html", {
        "items": items,
        "user": request.get("user")
    })
    return build_response(200, html)


@require_login
def toggle_wishlist(request):
    user_id = request["user_id"]
    product_id = request["form_data"].get("product_id")

    queries.toggle_wishlist(user_id, product_id)
    return redirect("/wishlist")
