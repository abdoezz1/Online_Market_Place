from items.handlers import product_detail, category_detail, filter_items

routes = [
    ('GET', '/products/product_<id>', product_detail),
    ('GET', '/products/category/<id>', category_detail),
    ('GET', '/filter', filter_items),
]