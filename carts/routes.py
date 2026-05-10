from carts.handlers import view_cart
from carts.handlers import add_to_cart
from carts.handlers import edit_order
from carts.handlers import remove_order
routes = [
    ("GET", "/home/cart", view_cart),
    ("GET", "/home/add-to-cart", add_to_cart),
    ("POST", "/home/edit-order/<id>", edit_order),
    ("POST", "/home/remove-order/<id>", remove_order),
]
