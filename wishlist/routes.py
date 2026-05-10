from wishlist.handlers import toggle_wishlist
from wishlist.handlers import view_wishlist


routes = [
    ("GET", "/wishlist", view_wishlist),
    ("POST", "/wishlist/toggle", toggle_wishlist),
]
