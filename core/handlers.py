from core.auth.session_manager import get_current_user, create_session, destroy_session, require_login, make_session_cookie, clear_session_cookie
from template_engine import render_template
from core.http.response_builder import build_response, redirect, error_response
from core.auth.auth import authenticate, register_user, hash_password, verify_password
import core.queries as q
from items.queries import get_home_items
from core.queries import get_all_categories
from core.queries import get_user_by_id


# ── Landing page ──────────────────────────────────────────────────────────────



def index(request):
    user_id = get_current_user(request)
    if user_id:
        return redirect('/home')
    html = render_template('core/index.html', {})
    return build_response(200, html)


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_page(request):
    user_id = get_current_user(request)
    if user_id:
        return redirect('/home')
    html = render_template('core/login.html', {'error': None})
    return build_response(200, html)


def login_submit(request):
    form = request.get('form_data', {})
    identifier = form.get('identifier', '').strip()
    password   = form.get('password', '').strip()

    user_id = authenticate(identifier, password)
    if not user_id:
        html = render_template('core/login.html', {'error': 'Invalid credentials.'})
        return build_response(200, html)

    session_key = create_session(user_id)
    return redirect('/home', cookies=[make_session_cookie(session_key)])


def signup_page(request):
    user_id = get_current_user(request)
    if user_id:
        return redirect('/home')
    html = render_template('core/signup.html', {'error': None})
    return build_response(200, html)


def signup_submit(request):
    form       = request.get('form_data', {})
    username   = form.get('username', '').strip()
    email      = form.get('email', '').strip()
    password   = form.get('password', '').strip()
    password2  = form.get('password2', '').strip()
    first_name = form.get('first_name', '').strip()
    last_name  = form.get('last_name', '').strip()

    if not all([username, email, password, first_name, last_name]):
        html = render_template('core/signup.html', {'error': 'All fields are required.'})
        return build_response(200, html)

    if password != password2:
        html = render_template('core/signup.html', {'error': 'Passwords do not match.'})
        return build_response(200, html)

    result = register_user(username, email, password, first_name, last_name)
    if not result.get('success'):
        # register_user returns a dict with 'error' key on failure
        html = render_template('core/signup.html', {'error': result.get('error', 'Registration failed.')})
        return build_response(200, html)

    return redirect('/login')


def logout(request):
    session_key = request.get('cookies', {}).get('sessionid')
    if session_key:
        destroy_session(session_key)
    return redirect('/login', cookies=[clear_session_cookie()])


# ── Profile ───────────────────────────────────────────────────────────────────

@require_login
def profile_page(request):
    user_id = get_current_user(request)
    user    = q.get_user_by_id(user_id)
    profile = q.get_user_profile(user_id)
    html = render_template('core/profile.html', {
        'user': user, 'profile': profile, 'error': None, 'success': None
    })
    return build_response(200, html)


@require_login
def profile_update(request):
    user_id = get_current_user(request)
    form    = request.get('form_data', {})

    first_name    = form.get('first_name', '').strip()
    last_name     = form.get('last_name', '').strip()
    phone         = form.get('phone', '').strip() or None
    address       = form.get('address', '').strip() or None
    bio           = form.get('bio', '').strip() or None
    date_of_birth = form.get('date_of_birth', '').strip() or None
    old_password  = form.get('old_password', '').strip()
    new_password  = form.get('new_password', '').strip()

    user    = q.get_user_by_id(user_id)
    profile = q.get_user_profile(user_id)

    # Password change (optional)
    if old_password or new_password:
        if not verify_password(old_password, user['password']):
            html = render_template('core/profile.html', {
                'user': user, 'profile': profile,
                'error': 'Old password is incorrect.', 'success': None
            })
            return build_response(200, html)
        if len(new_password) < 6:
            html = render_template('core/profile.html', {
                'user': user, 'profile': profile,
                'error': 'New password must be at least 6 characters.', 'success': None
            })
            return build_response(200, html)
        q.update_user_password(user_id, hash_password(new_password))

    q.update_user_names(user_id, first_name, last_name)
    q.update_user_profile(user_id, phone, address, bio, date_of_birth)

    user    = q.get_user_by_id(user_id)
    profile = q.get_user_profile(user_id)
    html = render_template('core/profile.html', {
        'user': user, 'profile': profile,
        'error': None, 'success': 'Profile updated successfully.'
    })
    return build_response(200, html)


# ── Static pages ──────────────────────────────────────────────────────────────

def about(request):
    html = render_template('core/about.html', {})
    return build_response(200, html)


def terms(request):
    html = render_template('core/terms.html', {})
    return build_response(200, html)


def contactus_page(request):
    html = render_template('core/contactus.html', {'success': None, 'error': None})
    return build_response(200, html)


def contactus_submit(request):
    form    = request.get('form_data', {})
    name    = form.get('name', '').strip()
    email   = form.get('email', '').strip()
    message = form.get('message', '').strip()

    if not all([name, email, message]):
        html = render_template('core/contactus.html', {
            'error': 'All fields are required.', 'success': None
        })
        return build_response(200, html)

    q.insert_contact_message(name, email, message)
    html = render_template('core/contactus.html', {
        'success': 'Message sent!', 'error': None
    })
    return build_response(200, html)


# ── Home ──────────────────────────────────────────────────────────────────────

@require_login
def home(request):
    user_id    = get_current_user(request)
    profile    = q.get_user_profile(user_id)
    items      = get_home_items(profile['id'])
    categories = get_all_categories()
    html = render_template('core/index.html', {
        'pro': items,
        'cat': categories,
        'user': q.get_user_by_id(user_id),
        'profile': profile,
    })
    return build_response(200, html)


# ── User detail (public) ──────────────────────────────────────────────────────

@require_login
def user_detail(request):
    profile_id = request.get('path_params', {}).get('id')
    if not profile_id:
        return error_response(404, 'User not found')

    public_profile = q.get_user_public_profile(profile_id)
    if not public_profile:
        return error_response(404, 'User not found')

    avg_rating = q.get_user_avg_rating(profile_id)
    user_items = q.get_user_for_sale_items(profile_id)

    user_id    = get_current_user(request)
    html = render_template('core/user_detail.html', {
        'public_profile': public_profile,
        'avg_rating': avg_rating,
        'user_items': user_items,
        'user': q.get_user_by_id(user_id),
    })
    return build_response(200, html)
