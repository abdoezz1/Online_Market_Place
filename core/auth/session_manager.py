"""
session_manager.py
Handles session creation, validation, destruction, and the @require_login decorator.
"""

import uuid
from datetime import datetime, timedelta
from functools import wraps

from core.db import db


SESSION_LIFETIME_HOURS = 24


# ─────────────────────────────────────────────
#  Session Lifecycle
# ─────────────────────────────────────────────

def create_session(user_id: int) -> str:
    """
    Create a new session for the given user_id.

    Steps:
      1. Generate a cryptographically random UUID as the session key.
      2. Calculate the expiry timestamp (now + SESSION_LIFETIME_HOURS).
      3. INSERT the session into the `sessions` table.

    Returns:
      session_key (str) — the value to place in the browser cookie.
    """
    session_key = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_LIFETIME_HOURS)

    db.execute_query(
        """
        INSERT INTO sessions (session_key, user_id, expires_at)
        VALUES (%s, %s, %s)
        """,
        (session_key, user_id, expires_at)
    )

    return session_key


def get_current_user(request_dict: dict):
    """
    Read the session cookie from an incoming request and return the logged-in user_id.

    Steps:
      1. Extract the 'sessionid' value from request cookies.
      2. Look up the session in the DB.
      3. Confirm the session has not expired.

    Args:
      request_dict: the parsed request dictionary produced by http_parser.
                    Expected keys: 'cookies' → dict.

    Returns:
      user_id (int) — if a valid, non-expired session exists.
      None          — if no session cookie, session not found, or session expired.
    """
    cookies = request_dict.get("cookies", {})
    session_key = cookies.get("sessionid")

    if not session_key:
        return None

    session = db.execute_query(
        """
        SELECT user_id, expires_at
        FROM sessions
        WHERE session_key = %s
        LIMIT 1
        """,
        (session_key,),
        fetch_one=True
    )

    if not session:
        return None  # Session key does not exist in DB

    # Check expiry — expires_at may come back as a datetime object from psycopg2
    expires_at = session["expires_at"]
    if isinstance(expires_at, datetime) and datetime.utcnow() > expires_at:
        # Expired — clean it up proactively
        destroy_session(session_key)
        return None

    return session["user_id"]


def destroy_session(session_key: str) -> None:
    """
    Invalidate a session (used on logout).
    Deletes the session row from the DB so the cookie can no longer be used.
    """
    if session_key:
        db.execute_query(
            "DELETE FROM sessions WHERE session_key = %s",
            (session_key,)
        )


# ─────────────────────────────────────────────
#  @require_login Decorator
# ─────────────────────────────────────────────

def require_login(handler_func):
    """
    Decorator for route handlers that require an authenticated user.

    Usage:
        @require_login
        def my_handler(request):
            user_id = request["user_id"]   # guaranteed to exist here
            ...

    Behaviour:
      - If the request has a valid session → injects user_id into request_dict
        under the key "user_id", then calls the original handler.
      - If there is no valid session → returns a 302 redirect to /login.

    The handler receives the same request dict it always would, but with
    "user_id" added so it never has to call get_current_user() itself.
    """
    @wraps(handler_func)
    def wrapper(request: dict):
        user_id = get_current_user(request)

        if user_id is None:
            from core.http.response_builder import redirect
            return redirect("/login")

        # 🔥 FETCH FULL USER OBJECT HERE
        from core.queries import get_user_by_id
        user = get_user_by_id(user_id)

        if not user:
            from core.http.response_builder import redirect
            return redirect("/login")

        # 🔥 THIS IS THE FIX
        request["user"] = user
        request["user_id"] = user_id

        return handler_func(request)

    return wrapper


# ─────────────────────────────────────────────
#  Helper — Build Set-Cookie Header Value
# ─────────────────────────────────────────────

def make_session_cookie(session_key: str) -> str:
    """
    Produce the Set-Cookie header value for a new session.
    Called by auth handlers (in core/handlers.py) after a successful login.

    Returns a string like:
      "sessionid=<key>; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400"
    """
    max_age = SESSION_LIFETIME_HOURS * 3600
    return (
        f"sessionid={session_key}; "
        f"HttpOnly; "
        f"SameSite=Lax; "
        f"Path=/; "
        f"Max-Age={max_age}"
    )


def clear_session_cookie() -> str:
    """
    Produce the Set-Cookie header value that clears the session cookie in the browser.
    Called by the logout handler after destroy_session().

    Returns:
      "sessionid=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
    """
    return "sessionid=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
