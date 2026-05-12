"""
inventory/handlers.py — Request Handlers for Inventory Module
================================================================

Handlers:
    inventory(request)          -> GET  /inventory
    add_item_page(request)      -> GET  /inventory/add_item
    add_item_submit(request)    -> POST /inventory/add_item
    item_detail(request)        -> GET  /inventory/item_detail_<id>
    edit_item_page(request)     -> GET  /inventory/<id>/edit
    edit_item_submit(request)   -> POST /inventory/<id>/edit
    delete_item(request)        -> POST /inventory/delete_item/<id>
    add_category(request)       -> POST /inventory/add-category
    remove_category(request)    -> POST /inventory/remove-category
    csv_upload(request)         -> POST /inventory/upload
    ai_description(request)     -> POST /inventory/ai-desc
"""

import os
import csv
import io
import uuid
import time
import traceback

from core.auth.session_manager import require_login
from core.http.response_builder import build_response, redirect, json_response, error_response
from inventory import queries

# Path where uploaded images are saved on disk
MEDIA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


# ─────────────────────────────────────────────────────────────────────────────
#  Helper — render HTML template (uses template_engine when ready,
#  otherwise returns a minimal page so handlers can be tested now)
# ─────────────────────────────────────────────────────────────────────────────

def _render(template_name, context=None):
    """Render a template. Falls back to a JSON dump if template_engine isn't ready."""
    try:
        from template_engine import render_template
        html = render_template(template_name, context or {})
        return build_response(200, html)
    except Exception as e:
        # Fallback to JSON if rendering fails
        import json
        from core.http.response_builder import json_response

        def _default(obj):
            from decimal import Decimal
            if isinstance(obj, Decimal):
                return float(obj)
            try:
                return str(obj)
            except Exception:
                return repr(obj)

        # Serialize context safely
        return json_response({
            "error": str(e),
            "template": template_name,
            "context": json.loads(json.dumps(context or {}, default=_default))
        }, status_code=500)


def _save_uploaded_file(file_dict):
    """
    Save an uploaded file to disk under media/photos/.
    Returns the relative path string for DB storage.
    """
    if not file_dict:
        return "default-product-image.jpg"

    filename = file_dict.get("filename", "upload.jpg")
    ext = os.path.splitext(filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"

    date_dir = time.strftime("%y/%m/%d")
    target_dir = os.path.join(MEDIA_ROOT, "photos", date_dir)
    os.makedirs(target_dir, exist_ok=True)

    filepath = os.path.join(target_dir, unique_name)
    with open(filepath, "wb") as f:
        f.write(file_dict["data"])

    return f"photos/{date_dir}/{unique_name}"


# ─────────────────────────────────────────────────────────────────────────────
#  GET /inventory — List user's own items
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def inventory(request):
    user_id = request["user_id"]
    items = queries.get_items_by_owner(user_id) or []
    categories = queries.get_all_categories() or []
    return _render("inventory/inventory.html", {
        "available_items": items,
        "categories": categories,
        "user": request.get("user"),
        "profile": request.get("profile"),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  GET /inventory/add_item — Render add item form
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def add_item_page(request):
    return _render("inventory/add_item.html", {
        "categories": queries.get_all_categories() or [],
        "user": request.get("user"),
        "profile": request.get("profile"),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  POST /inventory/add_item — Insert new item
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def add_item_submit(request):
    user_id = request["user_id"]
    form = request.get("form_data", {})
    files = request.get("files", {})

    name = form.get("name", "").strip()
    category_name = form.get("category", "").strip()
    price_str = form.get("price", "0")
    quantity_str = form.get("quantity", "1")
    description = form.get("description", "")

    # Validation
    if not name or not category_name:
        return _render("inventory/add_item.html", {
            "categories": queries.get_all_categories() or [],
            "error": "Please fill all required fields.",
        })

    try:
        price = float(price_str)
        quantity = int(quantity_str)
    except (ValueError, TypeError):
        return _render("inventory/add_item.html", {
            "categories": queries.get_all_categories() or [],
            "error": "Price must be a number and quantity must be an integer.",
        })

    image_file = files.get("image")
    image_path = None
    if image_file:
        image_path = _save_uploaded_file(image_file)

    # Get or create category
    category, _ = queries.get_or_create_category(category_name)

    # Insert item
    try:
        result = queries.insert_item(
            name=name,
            category_id=category["id"],
            price=price,
            description=description,
            image_path=image_path,
            quantity=quantity,
            for_sale=True,
            advertise=False,
            quantity_advertise=0,
            user_id=user_id,
        )
    except Exception as e:
        return _render("inventory/add_item.html", {
            "categories": queries.get_all_categories() or [],
            "user": request.get("user"),
            "profile": request.get("profile"),
            "error": f"Database error: {str(e)}",
        })

    if result:
        return redirect("/inventory")
    else:
        return _render("inventory/add_item.html", {
            "categories": queries.get_all_categories() or [],
            "user": request.get("user"),
            "profile": request.get("profile"),
            "error": "Failed to add item. Please try again.",
        })


# ─────────────────────────────────────────────────────────────────────────────
#  GET /inventory/item_detail_<id> — View item details
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def item_detail(request):
    item_id = request.get("path_params", {}).get("id")
    if not item_id:
        return error_response(400, "Missing item ID.")

    item = queries.get_item_by_id(int(item_id))
    if not item:
        return error_response(404, "Item not found.")

    return _render("inventory/item_detail.html", {
        "product": item,
        "user": request.get("user"),
        "profile": request.get("profile"),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  GET /inventory/<id>/edit — Render edit form
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def edit_item_page(request):
    user_id = request["user_id"]
    item_id = request.get("path_params", {}).get("id")
    if not item_id:
        return error_response(400, "Missing item ID.")

    item = queries.get_item_by_id(int(item_id))
    if not item:
        return error_response(404, "Item not found.")

    # Permission check
    if item["owner_user_id"] != user_id:
        return error_response(403, "You do not have permission to edit this item.")

    categories = queries.get_all_categories() or []
    return _render("inventory/edit_item.html", {
        "item": item,
        "categories": categories,
        "user": request.get("user"),
        "profile": request.get("profile"),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  POST /inventory/<id>/edit — Update item
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def edit_item_submit(request):
    user_id = request["user_id"]
    item_id = request.get("path_params", {}).get("id")
    if not item_id:
        return error_response(400, "Missing item ID.")

    item_id = int(item_id)

    # Permission check
    owner_uid = queries.get_item_owner_user_id(item_id)
    if owner_uid != user_id:
        return error_response(403, "You do not have permission to edit this item.")

    form = request.get("form_data", {})
    files = request.get("files", {})

    name = form.get("name", "").strip()
    category_name = form.get("category", "").strip()
    price_str = form.get("price", "0")
    quantity_str = form.get("quantity", "1")
    description = form.get("description", "")
    for_sale = form.get("for_sale", "off").lower() in ("on", "true", "1", "yes")
    advertise = form.get("advertise", "off").lower() in ("on", "true", "1", "yes")
    qty_adv_str = form.get("quantity_advertise", "0")

    try:
        price = float(price_str)
        quantity = int(quantity_str)
        quantity_advertise = int(qty_adv_str)
    except (ValueError, TypeError):
        return _render("inventory/edit_item.html", {
            "item": queries.get_item_by_id(item_id),
            "categories": queries.get_all_categories() or [],
            "user": request.get("user"),
            "profile": request.get("profile"),
            "error": "Price/quantity must be valid numbers.",
        })

    # Validate advertise quantity
    if advertise and quantity_advertise > quantity:
        return _render("inventory/edit_item.html", {
            "item": queries.get_item_by_id(item_id),
            "categories": queries.get_all_categories() or [],
            "user": request.get("user"),
            "profile": request.get("profile"),
            "error": "Quantity to advertise cannot exceed the total quantity.",
        })

    # Handle optional image upload
    image_file = files.get("image")
    image_path = _save_uploaded_file(image_file) if image_file else None

    # Resolve category
    category, _ = queries.get_or_create_category(category_name)

    try:
        result = queries.update_item(
            item_id=item_id,
            name=name,
            category_id=category["id"],
            price=price,
            description=description,
            image_path=image_path,
            quantity=quantity,
            for_sale=for_sale,
            advertise=advertise,
            quantity_advertise=quantity_advertise,
        )
    except Exception as e:
        return _render("inventory/edit_item.html", {
            "item": queries.get_item_by_id(item_id),
            "categories": queries.get_all_categories() or [],
            "user": request.get("user"),
            "profile": request.get("profile"),
            "error": f"Database error: {str(e)}",
        })

    if result:
        return redirect(f"/inventory/item_detail_{item_id}")
    else:
        return error_response(500, "Failed to update item.")


# ─────────────────────────────────────────────────────────────────────────────
#  POST /inventory/delete_item/<id> — Delete item
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def delete_item(request):
    user_id = request["user_id"]
    item_id = request.get("path_params", {}).get("id")
    if not item_id:
        return error_response(400, "Missing item ID.")

    item_id = int(item_id)

    # Permission check
    owner_uid = queries.get_item_owner_user_id(item_id)
    if owner_uid != user_id:
        return error_response(403, "You do not have permission to delete this item.")

    queries.delete_item_by_id(item_id)
    return redirect("/inventory")


# ─────────────────────────────────────────────────────────────────────────────
#  POST /inventory/add-category — Get or create category
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def add_category(request):
    form = request.get("form_data", {})
    name = form.get("name", "").strip()

    if not name:
        return redirect("/inventory")

    queries.get_or_create_category(name)
    return redirect("/inventory")


# ─────────────────────────────────────────────────────────────────────────────
#  POST /inventory/remove-category — Delete category if empty
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def remove_category(request):
    form = request.get("form_data", {})
    category_id = form.get("category_id")

    if not category_id:
        return redirect("/inventory")

    category_id = int(category_id)

    # Check if category has items
    item_count = queries.count_items_in_category(category_id)
    if item_count > 0:
        # Cannot delete — has items assigned
        return redirect("/inventory")

    queries.delete_category_by_id(category_id)
    return redirect("/inventory")


# ─────────────────────────────────────────────────────────────────────────────
#  POST /inventory/upload — CSV Bulk Insert (BONUS)
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def csv_upload(request):
    user_id = request["user_id"]
    files = request.get("files", {})
    csv_file = files.get("csv_file")

    if not csv_file:
        return json_response({"success": False, "error": "No CSV file uploaded."}, 400)

    try:
        text = csv_file["data"].decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))

        rows = []
        for row in reader:
            cat_name = row.get("category", "").strip()
            if not cat_name:
                continue
            category, _ = queries.get_or_create_category(cat_name)

            rows.append({
                "name": row.get("name", "Unnamed").strip(),
                "category_id": category["id"],
                "price": float(row.get("price", 0)),
                "description": row.get("description", ""),
                "quantity": int(row.get("quantity", 1)),
            })

        inserted = queries.bulk_insert_items(rows, user_id)
        return json_response({"success": True, "inserted": inserted})

    except Exception as e:
        traceback.print_exc()
        return json_response({"success": False, "error": str(e)}, 400)


# ─────────────────────────────────────────────────────────────────────────────
#  POST /inventory/ai-desc — AI Description Generator (BONUS)
# ─────────────────────────────────────────────────────────────────────────────

@require_login
def ai_description(request):
    """
    Accepts a product name (and optional category) via form_data or JSON body,
    calls the Gemini API to generate a product description,
    and returns the result as JSON.
    """
    form = request.get("form_data", {})
    product_name = form.get("product_name", "").strip()
    category_name = form.get("category", "").strip()

    if not product_name:
        return json_response({"success": False, "error": "Product name is required."}, 400)

    try:
        import google.generativeai as genai

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return json_response({"success": False, "error": "GEMINI_API_KEY not configured."}, 500)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = (
            f"Write a short, appealing product description (2-3 sentences) "
            f"for an online marketplace listing.\n"
            f"Product: {product_name}\n"
        )
        if category_name:
            prompt += f"Category: {category_name}\n"

        response = model.generate_content(prompt)
        description = response.text.strip()

        return json_response({"success": True, "description": description})

    except ImportError:
        return json_response({"success": False, "error": "google-generativeai package not installed."}, 500)
    except Exception as e:
        traceback.print_exc()
        return json_response({"success": False, "error": str(e)}, 500)

