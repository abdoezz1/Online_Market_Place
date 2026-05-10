from . import handlers as deposit_handlers

# Format: (Method, Path, Handler_Function)
# To be collected by router.py
routes = [
    ('GET',  '/deposit',          deposit_handlers.deposit_page),
    ('POST', '/deposit/process',  deposit_handlers.process_deposit),
]
