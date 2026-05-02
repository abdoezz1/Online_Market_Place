from core.handlers import (
    index, home, login_page, login_submit,
    signup_page, signup_submit, logout,
    profile_page, profile_update,
    about, contactus_page, contactus_submit,
    terms, user_detail
)

routes = [
    ('GET',  '/',            index),
    ('GET',  '/home',        home),
    ('GET',  '/login',       login_page),
    ('POST', '/login',       login_submit),
    ('GET',  '/signup',      signup_page),
    ('POST', '/signup',      signup_submit),
    ('GET',  '/logout',      logout),
    ('GET',  '/profile',     profile_page),
    ('POST', '/profile',     profile_update),
    ('GET',  '/about',       about),
    ('GET',  '/contactus',   contactus_page),
    ('POST', '/contactus',   contactus_submit),
    ('GET',  '/terms',       terms),
    ('GET',  '/user/<id>',   user_detail),
]