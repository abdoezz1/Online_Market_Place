"""
http_parser.py — HTTP Request Parser
=====================================

Translates raw HTTP bytes received from the client socket into a structured
Python dictionary that every handler in the application can work with.

This module is the **first step** in the request lifecycle:

    raw bytes  →  parse_request()  →  dict  →  router  →  handler

Public API
----------
- parse_request(raw_bytes)  — main entry point; returns a request dict.

Helper Functions
----------------
- parse_query_string(qs)        — ``a=1&b=2`` → ``{'a': '1', 'b': '2'}``
- parse_cookies(cookie_header)  — ``sid=abc; t=d`` → ``{'sid': 'abc', 't': 'd'}``
- parse_form_body(body, ct)     — dispatches to URL-encoded or multipart parser
- parse_multipart(body, boundary) — extracts files and text fields from multipart

"""

from urllib.parse import unquote_plus, unquote
from typing import Dict, Any, Tuple, Optional


# ─────────────────────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────────────────────

# Maximum number of headers to parse before giving up (DoS prevention).
_MAX_HEADERS = 100

# Default encoding assumed for text payloads.
_DEFAULT_ENCODING = "utf-8"

# MIME type strings used for dispatch.
_CT_URL_ENCODED = "application/x-www-form-urlencoded"
_CT_MULTIPART = "multipart/form-data"


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def parse_request(raw_bytes: bytes) -> Dict[str, Any]:
    """
    Parse raw HTTP request bytes into a structured dictionary.

    This is the **only function** that ``server.py`` needs to call.  It
    delegates to specialised helpers for query-strings, cookies, form bodies,
    and multipart uploads.

    Parameters
    ----------
    raw_bytes : bytes
        The complete HTTP request as received via ``socket.recv()``.  May
        include binary data in the case of file uploads.

    Returns
    -------
    dict
        A dictionary with the following keys:

        ============  ==========================================================
        Key           Description
        ============  ==========================================================
        method        HTTP verb (``'GET'``, ``'POST'``, etc.) — always uppercase
        path          URL path *without* the query string (``'/login'``)
        query_params  ``dict`` of query-string key/value pairs
        headers       ``dict`` of headers with title-cased keys
        body          raw body as a ``str`` (empty string if none)
        form_data     ``dict`` of parsed form fields (URL-encoded or multipart)
        cookies       ``dict`` of cookie name/value pairs
        files         ``dict`` of uploaded files — each value is a dict with
                      ``filename``, ``content_type``, and ``data`` (bytes)
        path_params   empty ``dict``; populated later by the router
        ============  ==========================================================

    Notes
    -----
    * If *raw_bytes* is empty or cannot be decoded the function returns a
      safe default dict rather than raising an exception.  This allows
      ``server.py`` to always continue its processing loop.
    * Header names are normalised to **title-case** (e.g. ``Content-Type``)
      so that look-ups are consistent throughout the application.

    Examples
    --------
    >>> raw = b"GET /home?q=shoes HTTP/1.1\\r\\nHost: localhost\\r\\n\\r\\n"
    >>> req = parse_request(raw)
    >>> req['method']
    'GET'
    >>> req['path']
    '/home'
    >>> req['query_params']
    {'q': 'shoes'}
    """
    # Provide a safe default so callers never crash on an empty request.
    default: Dict[str, Any] = _empty_request()

    if not raw_bytes or not raw_bytes.strip():
        return default

    try:
        # ── 1. Split head (text) from body (potentially binary) ──────────
        head_bytes, body_bytes = _split_head_body(raw_bytes)
        head_text = head_bytes.decode(_DEFAULT_ENCODING, errors="replace")

        # ── 2. Parse the request line ────────────────────────────────────
        lines = head_text.split("\r\n")
        if not lines or not lines[0].strip():
            return default

        method, path, query_params = _parse_request_line(lines[0])

        # ── 3. Parse headers ─────────────────────────────────────────────
        headers = _parse_headers(lines[1:])

        # ── 4. Parse cookies ─────────────────────────────────────────────
        cookies = parse_cookies(headers.get("Cookie", ""))

        # ── 5. Decode body text (best-effort) ────────────────────────────
        body_text = body_bytes.decode(_DEFAULT_ENCODING, errors="replace")

        # ── 6. Parse form data / file uploads ────────────────────────────
        content_type = headers.get("Content-Type", "")
        form_data, files = parse_form_body(body_bytes, content_type)

        return {
            "method": method,
            "path": path,
            "query_params": query_params,
            "headers": headers,
            "body": body_text,
            "form_data": form_data,
            "cookies": cookies,
            "files": files,
            "path_params": {},  # Filled in by router.py (Member 3)
        }

    except Exception:
        # Any unexpected parsing failure — return a safe default rather
        # than crashing the server thread.
        return default


# ─────────────────────────────────────────────────────────────────────────────
#  Query String
# ─────────────────────────────────────────────────────────────────────────────

def parse_query_string(qs: str) -> Dict[str, str]:
    """
    Parse a URL query string into a dictionary.

    Each key-value pair is split on ``&`` then on ``=``.  Both keys and
    values are **URL-decoded** (``%20`` → space, ``+`` → space).

    Parameters
    ----------
    qs : str
        The raw query string without the leading ``?``.
        Example: ``"name=John+Doe&age=30&city=New%20York"``

    Returns
    -------
    dict
        Decoded key/value pairs.  If a key appears more than once the
        **last** value wins (consistent with most web frameworks).

    Examples
    --------
    >>> parse_query_string("a=1&b=hello+world&c=%2Fpath")
    {'a': '1', 'b': 'hello world', 'c': '/path'}
    >>> parse_query_string("")
    {}
    """
    if not qs or not qs.strip():
        return {}

    params: Dict[str, str] = {}
    for pair in qs.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[unquote_plus(key)] = unquote_plus(value)
        elif pair.strip():
            # Bare key with no value (e.g. ``?debug``).
            params[unquote_plus(pair)] = ""

    return params


# ─────────────────────────────────────────────────────────────────────────────
#  Cookies
# ─────────────────────────────────────────────────────────────────────────────

def parse_cookies(cookie_header: str) -> Dict[str, str]:
    """
    Parse the value of the ``Cookie`` HTTP header into a dictionary.

    Cookies are separated by ``"; "`` (semicolon + space) and each cookie
    is a ``name=value`` pair.

    Parameters
    ----------
    cookie_header : str
        The raw ``Cookie`` header value.
        Example: ``"sessionid=abc123; theme=dark; lang=en"``

    Returns
    -------
    dict
        Cookie name/value pairs.

    Examples
    --------
    >>> parse_cookies("sessionid=abc123; theme=dark")
    {'sessionid': 'abc123', 'theme': 'dark'}
    >>> parse_cookies("")
    {}
    """
    if not cookie_header or not cookie_header.strip():
        return {}

    cookies: Dict[str, str] = {}
    for chunk in cookie_header.split(";"):
        chunk = chunk.strip()
        if "=" in chunk:
            name, value = chunk.split("=", 1)
            cookies[name.strip()] = value.strip()

    return cookies


# ─────────────────────────────────────────────────────────────────────────────
#  Form Body (URL-encoded & Multipart dispatcher)
# ─────────────────────────────────────────────────────────────────────────────

def parse_form_body(
    body: bytes,
    content_type: str,
) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """
    Parse the request body based on the ``Content-Type`` header.

    Dispatches to:

    * URL-encoded parser  — when ``Content-Type`` is
      ``application/x-www-form-urlencoded``
    * Multipart parser    — when ``Content-Type`` is
      ``multipart/form-data; boundary=...``

    Parameters
    ----------
    body : bytes
        The raw request body bytes (everything after the blank line).
    content_type : str
        The ``Content-Type`` header value.

    Returns
    -------
    tuple[dict, dict]
        A 2-tuple of ``(form_data, files)``.

        * ``form_data`` — ``dict`` of text field name → value.
        * ``files``     — ``dict`` of file field name → file info dict
          (``{'filename': str, 'content_type': str, 'data': bytes}``).
    """
    form_data: Dict[str, str] = {}
    files: Dict[str, Dict[str, Any]] = {}

    if not body:
        return form_data, files

    ct_lower = content_type.lower()

    if _CT_URL_ENCODED in ct_lower:
        # Standard HTML form submission.
        body_text = body.decode(_DEFAULT_ENCODING, errors="replace")
        form_data = parse_query_string(body_text)

    elif _CT_MULTIPART in ct_lower:
        # File upload or mixed form.
        boundary = _extract_boundary(content_type)
        if boundary:
            form_data, files = parse_multipart(body, boundary)

    return form_data, files


# ─────────────────────────────────────────────────────────────────────────────
#  Multipart Parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_multipart(
    body: bytes,
    boundary: str,
) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """
    Parse a ``multipart/form-data`` body into text fields and file uploads.

    The multipart format is used when HTML forms include ``<input type="file">``.
    Each part is delimited by ``--<boundary>`` and has its own headers
    (``Content-Disposition``, optionally ``Content-Type``).

    Parameters
    ----------
    body : bytes
        The raw request body (binary-safe).
    boundary : str
        The boundary string extracted from the ``Content-Type`` header.

    Returns
    -------
    tuple[dict, dict]
        ``(form_data, files)`` — see :func:`parse_form_body` for details.

    Notes
    -----
    * Text fields are decoded as UTF-8; file data is kept as raw ``bytes``.
    * If a part has a ``filename`` in its ``Content-Disposition`` header it is
      treated as a file upload; otherwise it is a text field.

    Examples
    --------
    Given a body like::

        --boundary123
        Content-Disposition: form-data; name="title"

        My Product
        --boundary123
        Content-Disposition: form-data; name="image"; filename="photo.jpg"
        Content-Type: image/jpeg

        <binary data>
        --boundary123--

    The function returns::

        (
            {'title': 'My Product'},
            {'image': {'filename': 'photo.jpg',
                       'content_type': 'image/jpeg',
                       'data': b'<binary data>'}}
        )
    """
    form_data: Dict[str, str] = {}
    files: Dict[str, Dict[str, Any]] = {}

    # The boundary in the body is prefixed with "--".
    delimiter = f"--{boundary}".encode(_DEFAULT_ENCODING)
    terminator = f"--{boundary}--".encode(_DEFAULT_ENCODING)

    # Split the body on the boundary delimiter.
    parts = body.split(delimiter)

    for part in parts:
        # Skip the preamble (before the first boundary) and the epilogue
        # (after the closing boundary marker).
        if not part or part.strip() == b"--" or part.strip() == b"":
            continue
        # Strip the terminator suffix if present.
        if part.endswith(terminator):
            part = part[: -len(terminator)]

        # Each part has headers separated from its value by \r\n\r\n.
        if b"\r\n\r\n" not in part:
            continue

        raw_headers, raw_value = part.split(b"\r\n\r\n", 1)

        # Remove the trailing \r\n that precedes the next boundary.
        if raw_value.endswith(b"\r\n"):
            raw_value = raw_value[:-2]

        headers_text = raw_headers.decode(_DEFAULT_ENCODING, errors="replace")

        # Parse the Content-Disposition header to extract field name and
        # optional filename.
        disposition = _find_header_in_part(headers_text, "Content-Disposition")
        if not disposition:
            continue

        field_name = _extract_directive(disposition, "name")
        if not field_name:
            continue

        filename = _extract_directive(disposition, "filename")

        if filename:
            # ── File upload ──────────────────────────────────────────────
            part_content_type = (
                _find_header_in_part(headers_text, "Content-Type")
                or "application/octet-stream"
            )
            files[field_name] = {
                "filename": filename,
                "content_type": part_content_type,
                "data": raw_value,  # kept as bytes
            }
        else:
            # ── Text field ───────────────────────────────────────────────
            form_data[field_name] = raw_value.decode(
                _DEFAULT_ENCODING, errors="replace"
            )

    return form_data, files


# ─────────────────────────────────────────────────────────────────────────────
#  Internal Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _empty_request() -> Dict[str, Any]:
    """Return a safe default request dict with all expected keys present."""
    return {
        "method": "GET",
        "path": "/",
        "query_params": {},
        "headers": {},
        "body": "",
        "form_data": {},
        "cookies": {},
        "files": {},
        "path_params": {},
    }


def _split_head_body(raw: bytes) -> Tuple[bytes, bytes]:
    """
    Split raw HTTP bytes into the head (request-line + headers) and the body.

    The HTTP specification mandates a blank line (``\\r\\n\\r\\n``) between
    the head and the body.  If no blank line is found the entire payload
    is treated as the head and the body is empty.

    Parameters
    ----------
    raw : bytes
        Complete raw HTTP request.

    Returns
    -------
    tuple[bytes, bytes]
        ``(head_bytes, body_bytes)``
    """
    separator = b"\r\n\r\n"
    if separator in raw:
        idx = raw.index(separator)
        return raw[:idx], raw[idx + len(separator):]
    return raw, b""


def _parse_request_line(line: str) -> Tuple[str, str, Dict[str, str]]:
    """
    Parse the first line of the HTTP request.

    Example input: ``"GET /search?q=shoes HTTP/1.1"``

    Parameters
    ----------
    line : str
        The raw request line (no trailing CRLF).

    Returns
    -------
    tuple[str, str, dict]
        ``(method, path, query_params)``

    Raises
    ------
    ValueError
        If the request line cannot be split into at least a method and a URI.
    """
    parts = line.strip().split(" ")
    if len(parts) < 2:
        raise ValueError(f"Malformed request line: {line!r}")

    method = parts[0].upper()
    raw_uri = parts[1]

    # Separate the path from the query string.
    if "?" in raw_uri:
        path, qs = raw_uri.split("?", 1)
        query_params = parse_query_string(qs)
    else:
        path = raw_uri
        query_params = {}

    # URL-decode the path itself (e.g. ``/my%20page`` → ``/my page``).
    path = unquote(path)

    return method, path, query_params


def _parse_headers(lines: list) -> Dict[str, str]:
    """
    Parse header lines into a dictionary with **title-cased** keys.

    Stops at the first empty line (which separates headers from body).
    Supports multi-line header folding (RFC 7230 §3.2.4 — obsolete but
    occasionally encountered).

    Parameters
    ----------
    lines : list[str]
        Header lines (without the request line), each ending implicitly
        at the ``\\r\\n`` that was split on.

    Returns
    -------
    dict
        Header name → value.  If a header appears more than once the
        values are concatenated with ``", "``.
    """
    headers: Dict[str, str] = {}
    count = 0

    for line in lines:
        if not line:
            break  # Blank line — end of headers.

        if count >= _MAX_HEADERS:
            break  # Safety limit to avoid abuse.

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().title()  # e.g. "content-type" → "Content-Type"
            value = value.strip()

            # RFC 7230: multiple headers with the same name are equivalent to
            # a single header whose value is a comma-separated list.
            if key in headers:
                headers[key] = f"{headers[key]}, {value}"
            else:
                headers[key] = value

            count += 1
        elif line[0] in (" ", "\t") and headers:
            # Obsolete line folding — append to the last header value.
            last_key = list(headers.keys())[-1]
            headers[last_key] += " " + line.strip()

    return headers


def _extract_boundary(content_type: str) -> Optional[str]:
    """
    Extract the ``boundary`` parameter from a ``Content-Type`` header.

    Parameters
    ----------
    content_type : str
        The full ``Content-Type`` value, e.g.
        ``"multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxk"``

    Returns
    -------
    str or None
        The boundary string without surrounding quotes, or ``None`` if
        not found.
    """
    for segment in content_type.split(";"):
        segment = segment.strip()
        if segment.lower().startswith("boundary="):
            boundary = segment.split("=", 1)[1].strip()
            # Remove surrounding quotes if present.
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]
            return boundary
    return None


def _find_header_in_part(headers_text: str, header_name: str) -> Optional[str]:
    """
    Find a specific header value within a multipart part's header block.

    Parameters
    ----------
    headers_text : str
        The raw header text of a single multipart part.
    header_name : str
        The header to search for (case-insensitive comparison).

    Returns
    -------
    str or None
        The header value if found, otherwise ``None``.
    """
    for line in headers_text.split("\r\n"):
        if ":" in line:
            name, value = line.split(":", 1)
            if name.strip().lower() == header_name.lower():
                return value.strip()
    return None


def _extract_directive(header_value: str, directive: str) -> Optional[str]:
    """
    Extract a named directive from a header value.

    Used primarily for parsing ``Content-Disposition`` directives such as
    ``name`` and ``filename``.

    Parameters
    ----------
    header_value : str
        e.g. ``'form-data; name="image"; filename="photo.jpg"'``
    directive : str
        e.g. ``"name"`` or ``"filename"``

    Returns
    -------
    str or None
        The unquoted directive value, or ``None`` if not found.

    Examples
    --------
    >>> _extract_directive('form-data; name="image"; filename="photo.jpg"', "name")
    'image'
    >>> _extract_directive('form-data; name="image"', "filename") is None
    True
    """
    search = f"{directive}="
    for segment in header_value.split(";"):
        segment = segment.strip()
        if segment.lower().startswith(search.lower()):
            value = segment.split("=", 1)[1].strip()
            # Remove surrounding quotes.
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            return value
    return None
