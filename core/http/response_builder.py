"""
response_builder.py — HTTP Response Builder
=============================================

Constructs valid HTTP/1.1 response byte-strings that ``server.py`` sends
back through the TCP socket to the client browser.

This module is the **last step** in the response lifecycle:

    handler  →  HTML string  →  build_response()  →  bytes  →  socket

Public API
----------
- build_response(status_code, body, ...)  — general-purpose response builder
- redirect(location, cookies)             — 302 redirect shortcut
- json_response(data, status_code)        — JSON API response
- error_response(status_code, message)    — styled HTML error page

Author : Member 2
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


# ─────────────────────────────────────────────────────────────────────────────
#  HTTP Status Code Registry
# ─────────────────────────────────────────────────────────────────────────────

_STATUS_TEXTS: Dict[int, str] = {
    200: "OK",
    201: "Created",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    413: "Payload Too Large",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def _status_text(code: int) -> str:
    """
    Return the standard reason phrase for an HTTP status code.

    Falls back to ``"Unknown"`` for codes not in our registry.

    Parameters
    ----------
    code : int
        The HTTP status code (e.g. 200, 404).

    Returns
    -------
    str
        Reason phrase such as ``"OK"`` or ``"Not Found"``.
    """
    return _STATUS_TEXTS.get(code, "Unknown")


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_response(
    status_code: int = 200,
    body: Union[str, bytes] = "",
    content_type: str = "text/html; charset=utf-8",
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[List[str]] = None,
) -> bytes:
    """
    Build a complete HTTP/1.1 response as raw bytes.

    This is the **core function** of the response builder.  All other public
    functions (``redirect``, ``json_response``, ``error_response``) delegate
    to this one.

    Parameters
    ----------
    status_code : int, default 200
        The HTTP status code for the response.
    body : str or bytes, default ``""``
        The response body.  If a ``str`` is given it is encoded to UTF-8.
    content_type : str, default ``"text/html; charset=utf-8"``
        Value for the ``Content-Type`` header.
    headers : dict or None, optional
        Additional headers to include in the response.  Keys should be
        valid HTTP header names (e.g. ``"X-Custom-Header"``).
    cookies : list[str] or None, optional
        A list of ``Set-Cookie`` header values.  Each string should be a
        complete cookie directive, for example the output of
        ``session_manager.make_session_cookie()``.

    Returns
    -------
    bytes
        A fully formed HTTP/1.1 response ready to be sent via
        ``socket.sendall()``.

    Notes
    -----
    The following headers are **always** included automatically:

    * ``Content-Type``
    * ``Content-Length`` — calculated from the encoded body
    * ``Connection: close`` — we don't support keep-alive
    * ``Date`` — current UTC timestamp in HTTP-date format

    Examples
    --------
    >>> resp = build_response(200, "<h1>Hello</h1>")
    >>> resp.startswith(b"HTTP/1.1 200 OK")
    True
    """
    # ── Encode body ──────────────────────────────────────────────────────
    body_bytes: bytes = body.encode("utf-8") if isinstance(body, str) else body

    # ── Assemble response headers ────────────────────────────────────────
    response_lines: List[str] = [
        f"HTTP/1.1 {status_code} {_status_text(status_code)}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
        f"Date: {_http_date()}",
    ]

    # Append caller-supplied headers.
    if headers:
        for key, value in headers.items():
            response_lines.append(f"{key}: {value}")

    # Append Set-Cookie headers (one line per cookie).
    if cookies:
        for cookie in cookies:
            response_lines.append(f"Set-Cookie: {cookie}")

    # ── Combine into final bytes ─────────────────────────────────────────
    header_block = "\r\n".join(response_lines)
    return f"{header_block}\r\n\r\n".encode("utf-8") + body_bytes


def redirect(
    location: str,
    cookies: Optional[List[str]] = None,
) -> bytes:
    """
    Build a **302 Found** redirect response.

    The browser will automatically navigate to the URL specified in the
    ``Location`` header.

    Parameters
    ----------
    location : str
        The URL to redirect to (e.g. ``"/login"`` or ``"/home"``).
    cookies : list[str] or None, optional
        ``Set-Cookie`` header values to include with the redirect
        (e.g. to set or clear a session cookie).

    Returns
    -------
    bytes
        A complete HTTP 302 response.

    Examples
    --------
    >>> resp = redirect("/login")
    >>> b"302 Found" in resp
    True
    >>> b"Location: /login" in resp
    True
    """
    return build_response(
        status_code=302,
        body="",
        headers={"Location": location},
        cookies=cookies,
    )


def json_response(
    data: Any,
    status_code: int = 200,
    cookies: Optional[List[str]] = None,
) -> bytes:
    """
    Build a JSON response with the appropriate ``Content-Type``.

    Serialises *data* to a JSON string using ``json.dumps()`` with
    ``ensure_ascii=False`` for proper Unicode support.

    Parameters
    ----------
    data : Any
        A JSON-serialisable Python object (dict, list, str, int, etc.).
    status_code : int, default 200
        The HTTP status code.
    cookies : list[str] or None, optional
        ``Set-Cookie`` header values to include.

    Returns
    -------
    bytes
        A complete HTTP response with ``Content-Type: application/json``.

    Examples
    --------
    >>> resp = json_response({"success": True, "user_id": 42})
    >>> b'"success": true' in resp
    True
    """
    body = json.dumps(data, ensure_ascii=False)
    return build_response(
        status_code=status_code,
        body=body,
        content_type="application/json; charset=utf-8",
        cookies=cookies,
    )


def error_response(status_code: int, message: str = "") -> bytes:
    """
    Build a styled HTML error page.

    Produces a minimal but visually clean error page that includes the
    status code, reason phrase, and an optional descriptive message.

    Parameters
    ----------
    status_code : int
        The HTTP error status code (e.g. 404, 500).
    message : str, default ``""``
        A human-readable explanation of what went wrong.  If empty, a
        generic message based on the status code is shown.

    Returns
    -------
    bytes
        A complete HTTP response containing the styled error page.

    Examples
    --------
    >>> resp = error_response(404, "The page you requested does not exist.")
    >>> b"404" in resp
    True
    """
    reason = _status_text(status_code)
    display_message = message if message else _default_error_message(status_code)

    html = _ERROR_PAGE_TEMPLATE.format(
        status_code=status_code,
        reason=reason,
        message=display_message,
    )

    return build_response(
        status_code=status_code,
        body=html,
        content_type="text/html; charset=utf-8",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Static File Response Helper
# ─────────────────────────────────────────────────────────────────────────────

def file_response(
    file_bytes: bytes,
    content_type: str = "application/octet-stream",
) -> bytes:
    """
    Build a response that serves a static file.

    Used by the router (Member 3) when serving files from ``/static/`` or
    ``/media/`` directories.

    Parameters
    ----------
    file_bytes : bytes
        The raw file content.
    content_type : str, default ``"application/octet-stream"``
        The MIME type of the file (e.g. ``"text/css"``, ``"image/png"``).

    Returns
    -------
    bytes
        A complete HTTP 200 response with the file as body.
    """
    return build_response(
        status_code=200,
        body=file_bytes,
        content_type=content_type,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _http_date() -> str:
    """
    Return the current UTC time in HTTP-date format (RFC 7231 §7.1.1.1).

    Example output: ``"Thu, 01 May 2026 12:30:00 GMT"``

    Returns
    -------
    str
        Formatted date string.
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%a, %d %b %Y %H:%M:%S GMT")


def _default_error_message(status_code: int) -> str:
    """
    Provide a generic user-friendly error message based on the status code.

    Parameters
    ----------
    status_code : int
        The HTTP error code.

    Returns
    -------
    str
        A human-readable description of what the error means.
    """
    messages = {
        400: "The server could not understand your request.",
        401: "You must be logged in to access this page.",
        403: "You do not have permission to access this resource.",
        404: "The page you are looking for does not exist.",
        405: "This HTTP method is not allowed for the requested URL.",
        500: "Something went wrong on our end. Please try again later.",
    }
    return messages.get(status_code, "An unexpected error occurred.")


# ─────────────────────────────────────────────────────────────────────────────
#  Error Page Template
# ─────────────────────────────────────────────────────────────────────────────

_ERROR_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} — {reason}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f8f9fa;
            color: #343a40;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .error-container {{
            text-align: center;
            padding: 3rem 2rem;
            max-width: 480px;
        }}
        .error-code {{
            font-size: 6rem;
            font-weight: 700;
            color: #dee2e6;
            line-height: 1;
        }}
        .error-reason {{
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0.5rem 0 1rem;
        }}
        .error-message {{
            font-size: 1rem;
            color: #6c757d;
            line-height: 1.6;
            margin-bottom: 2rem;
        }}
        .home-link {{
            display: inline-block;
            padding: 0.6rem 1.5rem;
            background-color: #343a40;
            color: #fff;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.9rem;
            transition: background-color 0.2s;
        }}
        .home-link:hover {{
            background-color: #495057;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">{status_code}</div>
        <div class="error-reason">{reason}</div>
        <p class="error-message">{message}</p>
        <a href="/home" class="home-link">Back to Home</a>
    </div>
</body>
</html>"""
