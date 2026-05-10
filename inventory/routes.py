"""
inventory/routes.py — URL Route Definitions for Inventory Module
=================================================================

Maps URL patterns to handler functions.
The router (Member 3) imports `routes` from each module and merges them.
"""

from inventory import handlers

routes = [
    # Method   Path pattern                          Handler
    ("GET",    "/inventory",                          handlers.inventory),
    ("GET",    "/inventory/add_item",                 handlers.add_item_page),
    ("POST",   "/inventory/add_item",                 handlers.add_item_submit),
    ("GET",    "/inventory/item_detail_{id}",         handlers.item_detail),
    ("GET",    "/inventory/{id}/edit",                handlers.edit_item_page),
    ("POST",   "/inventory/{id}/edit",                handlers.edit_item_submit),
    ("POST",   "/inventory/delete_item/{id}",         handlers.delete_item),
    ("POST",   "/inventory/add-category",             handlers.add_category),
    ("POST",   "/inventory/remove-category",          handlers.remove_category),
    ("POST",   "/inventory/upload",                   handlers.csv_upload),
    ("POST",   "/inventory/ai-desc",                  handlers.ai_description),
]

