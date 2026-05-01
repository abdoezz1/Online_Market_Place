"""
test_http.py — Unit Tests for http_parser.py & response_builder.py
======================================================================

Run with:  python test_http.py
"""

import sys
import json

# ── Import the modules under test ────────────────────────────────────────────
from http_parser import (
    parse_request,
    parse_query_string,
    parse_cookies,
    parse_form_body,
    parse_multipart,
)
from response_builder import (
    build_response,
    redirect,
    json_response,
    error_response,
    file_response,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Tiny test runner
# ─────────────────────────────────────────────────────────────────────────────

_pass = 0
_fail = 0


def assert_eq(label, actual, expected):
    """Assert equality and print pass/fail."""
    global _pass, _fail
    if actual == expected:
        _pass += 1
        print(f"  [PASS] {label}")
    else:
        _fail += 1
        print(f"  [FAIL] {label}")
        print(f"         expected: {expected!r}")
        print(f"         actual:   {actual!r}")


def assert_in(label, haystack, needle):
    """Assert that needle is contained in haystack."""
    global _pass, _fail
    if needle in haystack:
        _pass += 1
        print(f"  [PASS] {label}")
    else:
        _fail += 1
        print(f"  [FAIL] {label}")
        print(f"         could not find {needle!r} in output")


# ─────────────────────────────────────────────────────────────────────────────
#  1. parse_query_string
# ─────────────────────────────────────────────────────────────────────────────

print("\n== parse_query_string ==")

assert_eq(
    "basic key=value pairs",
    parse_query_string("a=1&b=2&c=3"),
    {"a": "1", "b": "2", "c": "3"},
)

assert_eq(
    "URL-encoded values (+ and %20)",
    parse_query_string("name=John+Doe&city=New%20York"),
    {"name": "John Doe", "city": "New York"},
)

assert_eq(
    "empty string returns empty dict",
    parse_query_string(""),
    {},
)

assert_eq(
    "bare key with no value",
    parse_query_string("debug"),
    {"debug": ""},
)

assert_eq(
    "duplicate keys — last value wins",
    parse_query_string("a=1&a=2"),
    {"a": "2"},
)


# ─────────────────────────────────────────────────────────────────────────────
#  2. parse_cookies
# ─────────────────────────────────────────────────────────────────────────────

print("\n== parse_cookies ==")

assert_eq(
    "multiple cookies",
    parse_cookies("sessionid=abc123; theme=dark; lang=en"),
    {"sessionid": "abc123", "theme": "dark", "lang": "en"},
)

assert_eq(
    "single cookie",
    parse_cookies("sessionid=xyz"),
    {"sessionid": "xyz"},
)

assert_eq(
    "empty header returns empty dict",
    parse_cookies(""),
    {},
)


# ─────────────────────────────────────────────────────────────────────────────
#  3. parse_request — GET
# ─────────────────────────────────────────────────────────────────────────────

print("\n== parse_request (GET) ==")

raw_get = (
    b"GET /home?page=2&sort=price HTTP/1.1\r\n"
    b"Host: localhost:8000\r\n"
    b"Accept: text/html\r\n"
    b"Cookie: sessionid=sess123; theme=light\r\n"
    b"\r\n"
)

req = parse_request(raw_get)
assert_eq("method", req["method"], "GET")
assert_eq("path", req["path"], "/home")
assert_eq("query_params", req["query_params"], {"page": "2", "sort": "price"})
assert_eq("Host header", req["headers"]["Host"], "localhost:8000")
assert_eq("cookies", req["cookies"], {"sessionid": "sess123", "theme": "light"})
assert_eq("body is empty", req["body"], "")
assert_eq("form_data is empty", req["form_data"], {})
assert_eq("path_params starts empty", req["path_params"], {})


# ─────────────────────────────────────────────────────────────────────────────
#  4. parse_request — POST (URL-encoded form)
# ─────────────────────────────────────────────────────────────────────────────

print("\n== parse_request (POST URL-encoded) ==")

raw_post = (
    b"POST /login HTTP/1.1\r\n"
    b"Host: localhost:8000\r\n"
    b"Content-Type: application/x-www-form-urlencoded\r\n"
    b"Content-Length: 29\r\n"
    b"Cookie: sessionid=abc\r\n"
    b"\r\n"
    b"username=admin&password=s3cr3t"
)

req = parse_request(raw_post)
assert_eq("method", req["method"], "POST")
assert_eq("path", req["path"], "/login")
assert_eq("form_data username", req["form_data"]["username"], "admin")
assert_eq("form_data password", req["form_data"]["password"], "s3cr3t")
assert_eq("cookie sessionid", req["cookies"]["sessionid"], "abc")


# ─────────────────────────────────────────────────────────────────────────────
#  5. parse_request — POST (multipart form / file upload)
# ─────────────────────────────────────────────────────────────────────────────

print("\n== parse_request (POST multipart) ==")

boundary = "----WebKitFormBoundary7MA4YWxk"
multipart_body = (
    f"------WebKitFormBoundary7MA4YWxk\r\n"
    f'Content-Disposition: form-data; name="title"\r\n'
    f"\r\n"
    f"My Product\r\n"
    f"------WebKitFormBoundary7MA4YWxk\r\n"
    f'Content-Disposition: form-data; name="image"; filename="photo.jpg"\r\n'
    f"Content-Type: image/jpeg\r\n"
    f"\r\n"
    f"FAKE_IMAGE_DATA\r\n"
    f"------WebKitFormBoundary7MA4YWxk--\r\n"
)

raw_multipart = (
    f"POST /inventory/add_item HTTP/1.1\r\n"
    f"Host: localhost:8000\r\n"
    f"Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxk\r\n"
    f"Content-Length: {len(multipart_body)}\r\n"
    f"\r\n"
    f"{multipart_body}"
).encode("utf-8")

req = parse_request(raw_multipart)
assert_eq("method", req["method"], "POST")
assert_eq("path", req["path"], "/inventory/add_item")
assert_eq("text field 'title'", req["form_data"].get("title"), "My Product")
assert_in("file 'image' present", req["files"], "image")
if "image" in req["files"]:
    assert_eq("filename", req["files"]["image"]["filename"], "photo.jpg")
    assert_eq("content_type", req["files"]["image"]["content_type"], "image/jpeg")


# ─────────────────────────────────────────────────────────────────────────────
#  6. parse_request — Edge cases
# ─────────────────────────────────────────────────────────────────────────────

print("\n== parse_request (edge cases) ==")

# Empty request
req = parse_request(b"")
assert_eq("empty bytes -> default method", req["method"], "GET")
assert_eq("empty bytes -> default path", req["path"], "/")

# None-ish request
req = parse_request(b"   ")
assert_eq("whitespace bytes -> default method", req["method"], "GET")

# Minimal request (no headers)
req = parse_request(b"GET / HTTP/1.1\r\n\r\n")
assert_eq("minimal GET method", req["method"], "GET")
assert_eq("minimal GET path", req["path"], "/")


# ─────────────────────────────────────────────────────────────────────────────
#  7. build_response
# ─────────────────────────────────────────────────────────────────────────────

print("\n== build_response ==")

resp = build_response(200, "<h1>Hello</h1>")
assert_in("status line", resp, b"HTTP/1.1 200 OK")
assert_in("Content-Type", resp, b"Content-Type: text/html")
assert_in("Content-Length", resp, b"Content-Length: 14")
assert_in("body present", resp, b"<h1>Hello</h1>")
assert_in("Connection close", resp, b"Connection: close")


# ─────────────────────────────────────────────────────────────────────────────
#  8. redirect
# ─────────────────────────────────────────────────────────────────────────────

print("\n== redirect ==")

resp = redirect("/login")
assert_in("302 status", resp, b"302 Found")
assert_in("Location header", resp, b"Location: /login")

# With cookie
resp = redirect("/home", cookies=["sessionid=abc; HttpOnly; Path=/"])
assert_in("Set-Cookie present", resp, b"Set-Cookie: sessionid=abc")


# ─────────────────────────────────────────────────────────────────────────────
#  9. json_response
# ─────────────────────────────────────────────────────────────────────────────

print("\n== json_response ==")

resp = json_response({"success": True, "user_id": 42})
assert_in("Content-Type JSON", resp, b"application/json")
assert_in("200 OK", resp, b"200 OK")
# Parse the body out to verify it's valid JSON
body_start = resp.index(b"\r\n\r\n") + 4
body_data = json.loads(resp[body_start:])
assert_eq("JSON success field", body_data["success"], True)
assert_eq("JSON user_id field", body_data["user_id"], 42)


# ─────────────────────────────────────────────────────────────────────────────
#  10. error_response
# ─────────────────────────────────────────────────────────────────────────────

print("\n== error_response ==")

resp = error_response(404, "Page not found.")
assert_in("404 status", resp, b"404 Not Found")
assert_in("custom message in body", resp, b"Page not found.")

resp = error_response(500)
assert_in("500 status", resp, b"500 Internal Server Error")
assert_in("default message", resp, b"Something went wrong")


# ─────────────────────────────────────────────────────────────────────────────
#  11. file_response
# ─────────────────────────────────────────────────────────────────────────────

print("\n== file_response ==")

resp = file_response(b"body { color: red; }", content_type="text/css")
assert_in("200 OK", resp, b"200 OK")
assert_in("Content-Type css", resp, b"Content-Type: text/css")
assert_in("CSS body", resp, b"body { color: red; }")


# ─────────────────────────────────────────────────────────────────────────────
#  12. Integration: session_manager import compatibility
# ─────────────────────────────────────────────────────────────────────────────

print("\n== Integration checks ==")

# Verify that `from response_builder import redirect` works
# (this is how session_manager.py imports it).
from response_builder import redirect as redirect_fn
assert_eq("redirect is callable", callable(redirect_fn), True)


# ─────────────────────────────────────────────────────────────────────────────
#  Summary
# ─────────────────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"  Results: {_pass} passed, {_fail} failed")
print(f"{'='*50}\n")

sys.exit(0 if _fail == 0 else 1)
