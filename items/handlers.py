from core.auth.session_manager import get_current_user, require_login
from template_engine import render_template
from core.http.response_builder import build_response, error_response
import items.queries as q
import core.queries as cq


@require_login
def product_detail(request):
    item_id = request.get('path_params', {}).get('id')
    if not item_id:
        return error_response(404, 'Product not found')

    item = q.get_item_by_id(item_id)
    if not item:
        return error_response(404, 'Product not found')

    q.increment_view_count(item_id)

    reviews    = q.get_item_reviews(item_id)
    user_id    = get_current_user(request)
    profile    = cq.get_user_profile(user_id)

    # Check if current user already reviewed this item
    user_reviewed = any(r['user_id'] == profile['id'] for r in (reviews or []))

    html = render_template('items/product_detail.html', {
        'item': item,
        'reviews': reviews,
        'user': cq.get_user_by_id(user_id),
        'profile': profile,
        'user_reviewed': user_reviewed,
    })
    return build_response(200, html)


@require_login
def category_detail(request):
    category_id = request.get('path_params', {}).get('id')
    if not category_id:
        return error_response(404, 'Category not found')

    category = q.get_category_by_id(category_id)
    if not category:
        return error_response(404, 'Category not found')

    items      = q.get_items_by_category(category_id)
    user_id    = get_current_user(request)

    html = render_template('items/category_detail.html', {
        'category': category,
        'items': items,
        'user': cq.get_user_by_id(user_id),
    })
    return build_response(200, html)


@require_login
def filter_items(request):
    params      = request.get('query_params', {})
    user_id     = get_current_user(request)
    profile     = cq.get_user_profile(user_id)

    name        = params.get('name', '').strip() or None
    min_price   = _to_float(params.get('min_price'))
    max_price   = _to_float(params.get('max_price'))
    min_rating  = _to_float(params.get('min_rating'))
    category_id = params.get('category_id') or None
    sort_by     = params.get('sort_by', 'newest')

    items      = q.filter_items(
        current_profile_id=profile['id'],
        name=name,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        category_id=category_id,
        sort_by=sort_by,
    )
    categories = cq.get_all_categories()

    html = render_template('items/filter.html', {
        'items': items,
        'categories': categories,
        'user': cq.get_user_by_id(user_id),
        'params': params,       # echo back so the form stays filled
    })
    return build_response(200, html)


# ── helpers ───────────────────────────────────────────────────────────────────

def _to_float(value):
    try:
        return float(value) if value not in (None, '') else None
    except (ValueError, TypeError):
        return None
