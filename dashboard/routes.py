from . import handlers as dashboard_handlers

# Mapping of (Method, Path, Handler) for Member 3's router
routes = [
    ('GET', '/dashboard', dashboard_handlers.dashboard_home),
    ('GET',  '/dashboard/transaction-report',            dashboard_handlers.transaction_report),
    ('GET',  '/dashboard/transaction/<id>/print',        dashboard_handlers.print_transaction),
    ('GET',  '/dashboard/deposit/<id>/print',            dashboard_handlers.print_deposit),
    ('GET',  '/dashboard/transaction/<id>/make-review',  dashboard_handlers.make_review_page),
    ('POST', '/dashboard/transaction/<id>/make-review',  dashboard_handlers.make_review_submit),
]
