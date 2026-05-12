from carts.handlers import (
    view_cart, add_to_cart, edit_order, remove_order, process_payment
)
routes = [
    ("GET", "/home/cart", view_cart),
    ("GET", "/home/add-to-cart", add_to_cart),
    ("POST", "/home/edit-order/<id>", edit_order),
    ("GET", "/home/remove-order/<id>", remove_order),
    ("GET", "/home/process-payment", process_payment),
]
