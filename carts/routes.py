routes = [
    ("GET", "/home/cart", "view_cart"),
    ("GET", "/home/add-to-cart", "add_to_cart"),
    ("POST", "/home/edit-order/<id>", "edit_order"),
    ("POST", "/home/remove-order/<id>", "remove_order"),
]
