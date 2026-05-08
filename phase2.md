# Phase 2 Implementation Plan v3 — Member Assignments & Big Picture

> **11 members | marketplace_server/ folder | Low-level sockets + threads + raw SQL**

---

## System Flow (How Your Code Connects)

```
User Browser
    │
    │ HTTP Request (e.g. GET /home)
    ▼
┌─────────────────────── server.py (Member 1) ───────────────────────┐
│  TCP Socket listens → accepts connection → spawns Thread           │
│  Thread reads raw bytes from socket                                │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────── http_parser.py (Member 2) ─────────────────────┐
│  Parses raw bytes → dict: {method, path, headers, form_data, ...} │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────── router.py (Member 3) ─────────────────────────┐
│  Matches path → finds handler function from module routes.py      │
│  Also serves /static/ and /media/ files                           │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─── session_manager.py (Member 4) ──┐   ┌─── auth.py (Member 4) ──┐
│  Reads session cookie → looks up   │   │  bcrypt hash/verify      │
│  user_id from sessions DB table    │   │  register_user()         │
│  require_login() decorator         │   │  authenticate()          │
└────────────────────────────────────┘   └──────────────────────────┘
                             ▼
┌────────── {module}/handlers.py (Members 7-10) ────────────────────┐
│  Business logic: read form data, call queries, render template    │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌────────── {module}/queries.py (Members 7-10) ─────────────────────┐
│  Raw SQL functions using db.execute_query()                       │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌──────────────────── db.py (Member 5) ─────────────────────────────┐
│  psycopg2 ThreadedConnectionPool → PostgreSQL                     │
│  execute_query(sql, params) and execute_transaction(queries_list) │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌────────── template_engine.py (Member 6) ──────────────────────────┐
│  Jinja2 render_template(name, context) → HTML string              │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
┌────────── response_builder.py (Member 2) ─────────────────────────┐
│  Wraps HTML in HTTP/1.1 200 OK headers → bytes                    │
└────────────────────────────┬───────────────────────────────────────┘
                             ▼
                    server.py sends bytes back
                    through the socket → Browser renders page
```

---

## MEMBER 1 — Server Lead

### Files
| File | Role |
|---|---|
| `server.py` | **PRIMARY** — the main entry point |

### What To Build
Create a TCP server using Python's `socket` module that:
1. Creates a `socket.socket(AF_INET, SOCK_STREAM)`
2. Binds to `0.0.0.0:8000` and calls `listen()`
3. Runs an infinite loop calling `accept()` for new connections
4. For each connection, spawns a `threading.Thread` that:
   - Reads raw bytes from the client socket (`recv()`)
   - Passes bytes to `http_parser.parse_request()` → gets a dict
   - Passes the dict to `router.route()` → gets response bytes
   - Sends response bytes back via `socket.sendall()`
   - Closes the socket
5. Handles errors: client disconnect, empty request, Ctrl+C shutdown

### Edge Cases
- Large POST bodies (file uploads): loop `recv()` until `Content-Length` bytes are read
- Browser sends empty keep-alive pings: return empty 200
- Multiple threads accessing shared resources: no global mutable state

### Big Picture
**You are the foundation. Without server.py, nobody's code can run.** Every HTTP request enters through your file. Every response leaves through your file. You are the "Gunicorn replacement." If your socket server breaks, the entire application is down. Team 1 & 2 depend on you finishing by Day 2 so they can test their work.

---

## MEMBER 2 — HTTP Parser

### Files
| File | Role |
|---|---|
| `http_parser.py` | **PRIMARY** — parse incoming requests |
| `response_builder.py` | **PRIMARY** — build outgoing responses |

### What To Build in http_parser.py
A `parse_request(raw_bytes)` function that converts raw HTTP into a dict:

**Input:** `b"POST /login HTTP/1.1\r\nContent-Type: application/x-www-form-urlencoded\r\nCookie: sessionid=abc\r\n\r\nusername=admin&password=123"`

**Output:**
```python
{
    'method': 'POST',
    'path': '/login',
    'query_params': {},
    'headers': {'Content-Type': '...', 'Cookie': 'sessionid=abc'},
    'body': 'username=admin&password=123',
    'form_data': {'username': 'admin', 'password': '123'},
    'cookies': {'sessionid': 'abc'},
    'path_params': {}
}
```

Helper functions needed:
- `parse_query_string(qs)` → split on `&` then `=`
- `parse_cookies(cookie_header)` → split on `; ` then `=`
- `parse_form_body(body, content_type)` → URL-encoded or multipart
- `parse_multipart(body, boundary)` → extract file uploads

### What To Build in response_builder.py
Functions to create valid HTTP response bytes:
- `build_response(status_code, body, content_type, headers, cookies)` → bytes
- `redirect(location, cookies)` → 302 response bytes
- `json_response(data, status_code)` → JSON response bytes
- `error_response(status_code, message)` → error page bytes

### Big Picture
**You are the translator.** The browser speaks raw HTTP bytes. Python handlers speak dictionaries. You translate in both directions. Every single handler in every module depends on your parser giving them clean data, and your response builder wrapping their HTML correctly. If your parser misreads a form field, logins break. If your response builder forgets `Content-Length`, browsers hang.

---

## MEMBER 3 — Router & Static Files

### Files
| File | Role |
|---|---|
| `router.py` | **PRIMARY** — URL matching + static file serving |
| All `*/routes.py` | **READ** — imports route lists from every module |

### What To Build
1. **Path matcher:** Convert patterns like `/products/product_<id>` into regex, match against actual paths like `/products/product_42`, extract `{'id': '42'}`
2. **Main route function:** Collect routes from all modules, loop through them, find match, call handler
3. **Static file server:** If path starts with `/static/`, read file from `static/` directory, detect MIME type (`text/css`, `image/png`, etc.), return file bytes
4. **Media file server:** Same for `/media/` (user-uploaded images)

### Routes to collect (from each module's routes.py)
- `core/routes.py`: `/`, `/home`, `/login`, `/signup`, `/logout`, `/profile`, `/about`, `/contactus`, `/terms`, `/user/<id>`
- `items/routes.py`: `/products/product_<id>`, `/products/category/<id>`, `/filter`
- `carts/routes.py`: `/home/cart`, `/home/add-to-cart`, `/home/edit-order/<id>`, `/home/remove-order/<id>`, `/home/process-payment`
- `deposit/routes.py`: `/deposit`, `/deposit/process`
- `dashboard/routes.py`: `/dashboard/transaction-report`, `/dashboard/transaction/<id>/print`, `/dashboard/deposit/<id>/print`, `/dashboard/transaction/<id>/make-review`
- `inventory/routes.py`: `/inventory`, `/inventory/add_item`, `/inventory/<id>/edit`, `/inventory/delete_item/<id>`, `/inventory/add-category`, `/inventory/remove-category`, `/inventory/upload`, `/inventory/ai-desc`
- `wishlist/routes.py`: `/wishlist`, `/wishlist/toggle`
- `messages/routes.py`: `/messages`, `/messages/<user_id>`, `/messages/send`

### Big Picture
**You are the traffic controller.** When a request comes in for `/home`, you decide it goes to `core/handlers.py`. When it's for `/inventory`, you send it to `inventory/handlers.py`. Without you, every request gets a 404. You also serve all CSS, JS, and images — without that, the site loads with no styling.

---

## MEMBER 4 — Auth & Sessions

### Files
| File | Role |
|---|---|
| `auth.py` | **PRIMARY** — password hashing + user registration + login verification |
| `session_manager.py` | **PRIMARY** — cookie-based session management |

### What To Build in auth.py
- `hash_password(plain_text)` → uses `bcrypt.hashpw()` to create salted hash
- `verify_password(plain_text, hashed)` → uses `bcrypt.checkpw()`
- `register_user(username, email, password, first_name, last_name)` → checks uniqueness, hashes password, INSERTs into `users` + `user_profiles` tables
- `authenticate(identifier, password)` → looks up user by username OR email, verifies password, returns user_id or None

### What To Build in session_manager.py
- `create_session(user_id)` → generates UUID session key, INSERTs into `sessions` table, returns key
- `get_current_user(request_dict)` → reads `sessionid` cookie, looks up in DB, returns user_id if valid and not expired
- `destroy_session(session_key)` → DELETEs from `sessions` table (logout)
- `require_login(handler_func)` → decorator that checks session before calling handler, redirects to `/login` if not logged in

### Big Picture
**You are the security guard.** Without you, anyone can access any page without logging in. Every handler that needs to know "who is the current user?" calls your `get_current_user()`. Every protected page uses your `@require_login` decorator. If your session manager breaks, users get logged out randomly. If your password hashing breaks, nobody can register or log in.

---

## MEMBER 5 — Database Manager

### Files
| File | Role |
|---|---|
| `db.py` | **PRIMARY** — database connection pool + query execution |
| `config.py` | **PRIMARY** — all configuration values |
| `sql/schema.sql` | **PRIMARY** — DDL to create all tables |
| `sql/seed.sql` | **PRIMARY** — sample test data |

### What To Build in db.py
- `ThreadedConnectionPool` from psycopg2 (min=1, max=20 connections) — **critical for thread safety**
- `execute_query(sql, params, fetch_one, fetch_all)` → gets connection from pool, executes query, returns results as dict(s), returns connection to pool
- `execute_transaction(queries_list)` → runs multiple queries atomically (all succeed or all rollback) — **critical for payment processing**

### What To Build in config.py
- Load `.env` file using `python-dotenv`
- Export: `SERVER_HOST`, `SERVER_PORT`, `DB_CONFIG` dict, `SECRET_KEY`, `TEMPLATE_DIR`, `STATIC_DIR`, `MEDIA_DIR`

### What To Build in sql/schema.sql
- Copy full DDL from `DB code.md` (13 tables)
- **ADD** the `sessions` table (session_key, user_id, expires_at)
- **ADD** partitioning statements (Transaction=HASH, Items=RANGE, Deposit=LIST, etc.)

### What To Build in sql/seed.sql
- 3-5 test users with bcrypt-hashed passwords
- 5-10 categories
- 20+ sample items
- A few test transactions, deposits, and an API client

### Big Picture
**You are the data backbone.** Every single module calls your `execute_query()` to read and write data. Your `ThreadedConnectionPool` prevents threads from fighting over database connections (without it, the app crashes under load). Your `execute_transaction()` ensures that when someone buys an item, the money transfer and stock reduction happen atomically — if any step fails, everything rolls back. If your DB layer breaks, the entire app has no data.

---

## MEMBER 6 — Templates & UI

### Files
| File | Role |
|---|---|
| `template_engine.py` | **PRIMARY** — Jinja2 environment setup |
| `templates/` (all HTML files) | **PRIMARY** — convert 24+ templates from Django to Jinja2 |
| `static/` | **COPY** — copy CSS/JS/images from old project |

### What To Build in template_engine.py
- Create `jinja2.Environment` with `FileSystemLoader` pointing to `templates/`
- `render_template(template_name, context)` → returns HTML string

### Template Conversion Work
Copy every `.html` from `SALES_square/templates/` into `marketplace_server/templates/` preserving subfolder structure, then apply these changes:

| Find (Django) | Replace With (Jinja2) |
|---|---|
| `{% load static %}` | *(delete line)* |
| `{% static 'css/style.css' %}` | `/static/css/style.css` |
| `{% url 'home' %}` | `/home` |
| `{% url 'product_detail' item.id %}` | `/products/product_{{ item.id }}` |
| `{% csrf_token %}` | *(delete line)* |
| `{% if request.user.is_authenticated %}` | `{% if user %}` |
| `{{ request.user.username }}` | `{{ user.username }}` |

**Templates to convert (24 files):**
- `base.html`, `core/` (8 files), `items/` (2), `carts/cart.html`, `deposit/deposit.html`, `dashboard/` (4), `inventory/` (4), `parts/` (3)

**New templates to create from scratch (3 files):**
- `wishlist/wishlist.html`, `messages/inbox.html`, `messages/conversation.html`

### Static Files
Copy `SALES_square/Test/static/` → `marketplace_server/static/` (all CSS, JS, images)

### Big Picture
**You are the face of the application.** Users never see Python code — they see your HTML. Every handler in every module calls your `render_template()` to produce the page the user sees. If a template has a syntax error, that page crashes. If you forget to convert a `{% url %}` tag, links break. The 3 new templates (wishlist, messages) are features that didn't exist before — you're creating them fresh.

---

## MEMBER 7 — Home Page, Catalog & Search

### Files
| File | Role |
|---|---|
| `core/handlers.py` | **PRIMARY** — home, about, contact, terms, user_detail, profile |
| `core/queries.py` | **PRIMARY** — SQL for users, profiles, contacts |
| `core/routes.py` | **PRIMARY** — route definitions |
| `items/handlers.py` | **PRIMARY** — product detail, category, search |
| `items/queries.py` | **PRIMARY** — SQL for items, categories, reviews |
| `items/routes.py` | **PRIMARY** — route definitions |

### Handlers To Build
| Handler | Route | What It Does |
|---|---|---|
| `index` | `GET /` | Render landing page |
| `home` | `GET /home` | Fetch all for_sale items (exclude own), render with categories |
| `profile` | `GET /profile` | Show current user profile |
| `profile_update` | `POST /profile` | Update user info + password change |
| `about` | `GET /about` | Render static about page |
| `contactus_page` | `GET /contactus` | Render contact form |
| `contactus_submit` | `POST /contactus` | INSERT into contact_messages |
| `terms` | `GET /terms` | Render static terms page |
| `user_detail` | `GET /user/<id>` | Show user's products + avg rating |
| `product_detail` | `GET /products/product_<id>` | Show item + reviews + increment view_count |
| `category_detail` | `GET /products/category/<id>` | Show items in category |
| `filter_items` | `GET /filter` | Dynamic search: name, price range, rating, sort |

### Key SQL Queries To Write
- `SELECT * FROM items WHERE for_sale=TRUE AND owned_by_id != %s`
- `SELECT * FROM items WHERE id=%s` + `UPDATE items SET view_count=view_count+1`
- Dynamic filter: `WHERE price BETWEEN %s AND %s AND average_rating >= %s ORDER BY ...`
- `SELECT AVG(rating) FROM reviews WHERE product_id IN (SELECT id FROM items WHERE owned_by_id=%s)`

### Big Picture
**You build what users see 80% of the time** — the home page, the search, and the product pages. The home page is the first thing users see after login. The search feature (price range, rating filter, sorting) is a major new feature that didn't exist in the old project. Product detail with view_count tracking is also new. If your handlers break, users can't browse or find products.

---

## MEMBER 8 — Cart, Wishlist & Messages

### Files
| File | Role |
|---|---|
| `carts/handlers.py` | **PRIMARY** — cart view, add/edit/remove |
| `carts/routes.py` | **PRIMARY** — route definitions |
| `wishlist/handlers.py` | **PRIMARY** — view + toggle wishlist |
| `wishlist/queries.py` | **PRIMARY** — SQL for wishlist |
| `wishlist/routes.py` | **PRIMARY** — route definitions |
| `messages/handlers.py` | **PRIMARY** — inbox, conversation, send |
| `messages/queries.py` | **PRIMARY** — SQL for messages |
| `messages/routes.py` | **PRIMARY** — route definitions |

### Handlers To Build
| Handler | Route | What It Does |
|---|---|---|
| `view_cart` | `GET /home/cart` | List all cart items with prices |
| `add_to_cart` | `GET /home/add-to-cart?product_id=X&qty=Y` | Add item or increment existing |
| `edit_order` | `POST /home/edit-order/<id>` | Change quantity |
| `remove_order` | `POST /home/remove-order/<id>` | Delete from cart |
| `view_wishlist` | `GET /wishlist` | Show wishlisted products |
| `toggle_wishlist` | `POST /wishlist/toggle` | Add if not exists, remove if exists |
| `inbox` | `GET /messages` | List conversations |
| `conversation` | `GET /messages/<user_id>` | Show messages with a user |
| `send_message` | `POST /messages/send` | Insert new message |

### Big Picture
**You own three features — one existing (cart) and two brand new (wishlist + messages).** The cart is the core purchasing flow: users can't buy anything without it. Wishlist and messages are entirely new features that your team is adding to differentiate the project. 


## MEMBER 9 — Payments, Deposits & Dashboard

### Files
| File | Role |
|---|---|
| `carts/queries.py` | **PRIMARY** — all payment processing SQL |
| `deposit/handlers.py` | **PRIMARY** — deposit page + processing |
| `deposit/queries.py` | **PRIMARY** — deposit SQL |
| `deposit/routes.py` | **PRIMARY** — route definitions |
| `dashboard/handlers.py` | **PRIMARY** — reports, receipts, reviews |
| `dashboard/queries.py` | **PRIMARY** — transaction/deposit/review SQL |
| `dashboard/routes.py` | **PRIMARY** — route definitions |

### Critical: Payment Processing (in carts/queries.py)
The payment flow must use `db.execute_transaction()` to be atomic:
1. `UPDATE user_profiles SET balance = balance - total WHERE id = buyer_id`
2. `UPDATE user_profiles SET balance = balance + total WHERE id = seller_id`
3. Check if buyer already owns a copy → UPDATE qty or INSERT new item
4. `INSERT INTO payments (...)`
5. `INSERT INTO transactions (...)`
6. `UPDATE items SET quantity = quantity - qty WHERE id = product_id`
7. `DELETE FROM orders WHERE id = order_id`

**ALL 7 steps must succeed or ALL roll back.** This is the most critical code in the entire project.

### Deposit Validation (CHANGED rules)
- Card: exactly 16 digits, starts with 4 or 5
- CVC: exactly 3 digits
- Amount: between 10 and 10,000
- Max 3 deposits per day per user

### Dashboard Handlers
- `transaction_report`: staff sees ALL, normal user sees own only
- `print_transaction` / `print_deposit`: receipt views
- `make_review`: validate 1 review per user per product per transaction, recalculate avg rating

### Big Picture
**You handle all the money.** Payment processing is the most complex and dangerous code in the project — if it's not atomic, users could lose money or get free items. Deposits are how users add funds. The dashboard is how users track their financial history. If your transaction code has a bug, the entire marketplace economy breaks. The `execute_transaction()` from Member 5 is your best friend.

---

## MEMBER 10 — Inventory & File Uploads

### Files
| File | Role |
|---|---|
| `inventory/handlers.py` | **PRIMARY** — CRUD for items + categories + CSV + AI |
| `inventory/queries.py` | **PRIMARY** — inventory SQL |
| `inventory/routes.py` | **PRIMARY** — route definitions |

### Handlers To Build
| Handler | Route | What It Does |
|---|---|---|
| `inventory` | `GET /inventory` | List user's own items |
| `add_item_page/submit` | `GET/POST /inventory/add_item` | Form + create item + image upload |
| `item_detail` | `GET /inventory/item_detail_<id>` | View own item details |
| `edit_item_page/submit` | `GET/POST /inventory/<id>/edit` | Edit item form + update |
| `delete_item` | `POST /inventory/delete_item/<id>` | Delete item |
| `add_category` | `POST /inventory/add-category` | Create category |
| `remove_category` | `POST /inventory/remove-category` | Delete if empty |
| `csv_upload` | `POST /inventory/upload` | Parse CSV, bulk insert (BONUS) |
| `ai_description` | `POST /inventory/ai-desc` | Call Gemini API (BONUS) |

### Image Upload Challenge
You must parse `multipart/form-data` from the raw HTTP body to extract uploaded files. Save images to `media/product_images/` and store the path in DB.

### Big Picture
**You control the supply side of the marketplace.** Sellers can't list products without your inventory handlers. The CSV upload feature lets sellers add 100 products at once instead of one by one . The AI description generator using Google Gemini is a "wow factor" bonus feature. Image uploads are technically the hardest part because you're parsing binary file data from raw HTTP.

---

## MEMBER 11 — REST API Developer

### Files
| File | Role |
|---|---|
| `external_api/` | **PRIMARY** — Django/DRF server (separate project) |
| Existing `SALES_square/` code | **REFERENCE** — reuse existing API code |

### What To Do
1. Copy the `SALES_square` Django project (or reference it)
2. Update `settings.py`: change database from SQLite to PostgreSQL (same DB as marketplace_server)
3. Keep existing DRF views, serializers, and API key authentication
4. Run on **port 8001**: `python manage.py runserver 0.0.0.0:8001`

### Endpoints (7 total)
| Endpoint | Method | Auth | What It Does |
|---|---|---|---|
| `/api/signup/` | POST | None | User registration |
| `/api/login/` | POST | None | User login |
| `/deposit/process-payment/` | POST | Session | Process deposit |
| `/external_api/api/products/` | GET | API Key | List advertised products |
| `/external_api/api/create_order/` | POST | API Key | Create order from external store |
| `/inventory/upload/` | POST | Session | CSV bulk upload (BONUS) |
| `/inventory/ai-desc/` | POST | Session | AI description via Gemini (BONUS) |

### Big Picture
**You are the bridge to the outside world.** The main app (port 8000) serves humans via browsers. Your API (port 8001) serves external applications programmatically. External stores use your API to browse products and place orders without ever visiting the website. This is the only part of the project that keeps using Django/DRF — which means you have the easiest framework setup, but you must ensure both servers share the same PostgreSQL database so data stays in sync.

---

## Timeline Summary

Members 1,2,4,5,6 ==> deadline next sunday 3/5
Members 7,8,9,10 must finish route files by sunday 3/5 , rest files ==> deadline next thursday 7/5
Members 3,11 ==> deadline next thursday 7/5 
### Key Dependencies
- **Everyone** depends on Member 1 (server) + Member 2 (parser) + Member 5 (db.py) — these must be done first
- **Members 7-10** depend on Member 4 (sessions) for `@require_login`
- **Members 7-10** depend on Member 6 (templates) for `render_template()`
- **Member 9** depends on Member 5's `execute_transaction()` for atomic payments
- **Member 11** works independently (separate Django server)
