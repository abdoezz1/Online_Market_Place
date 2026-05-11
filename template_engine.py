"""
template_engine.py — Jinja2 template rendering engine for marketplace_server.
Usage:
    from template_engine import render_template
    html = render_template("core/index.html", {"user": user, "products": products})
"""
import os
import jinja2
from typing import Optional
from datetime import datetime

# Resolve the templates directory relative to this file
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_TEMPLATES_DIR = os.path.join(_BASE_DIR, "templates")

# ---------------------------------------------------------------------------
# Jinja2 environment
# ---------------------------------------------------------------------------
_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
    # Keep undefined variables silent (renders as empty string)
    undefined=jinja2.ChainableUndefined,
    # Trim whitespace around block tags for cleaner HTML output
    trim_blocks=True,
    lstrip_blocks=True,
)

# ---------------------------------------------------------------------------
# Globals (available in every template automatically)
# ---------------------------------------------------------------------------
_env.globals['now'] = datetime.now

# ---------------------------------------------------------------------------
# Custom filters
# ---------------------------------------------------------------------------
def _strftime_filter(value, fmt="%b %d, %Y"):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime(fmt)

_env.filters["strftime"] = _strftime_filter

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def render_template(template_name: str, context: Optional[dict] = None) -> str:
    """Render a Jinja2 template and return the HTML string.
    Args:
        template_name: Path relative to the templates/ directory,
                       e.g. "core/index.html" or "carts/cart.html".
        context:       Dictionary of variables exposed inside the template.
                       Pass ``None`` or omit for an empty context.
    Returns:
        Rendered HTML as a string.
    Raises:
        jinja2.TemplateNotFound: If *template_name* does not exist.
        jinja2.TemplateError:    On any other Jinja2 rendering error.
    """
    if context is None:
        context = {}
    
    context.setdefault('cart_items_count', 0)
    template = _env.get_template(template_name)
    return template.render(**context)
