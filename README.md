# Online Market Place

Online Market Place is a Python-based marketplace web application built around a custom HTTP stack, server-rendered Jinja2 templates, and a PostgreSQL-backed data layer. The codebase is organized into focused feature packages for storefront browsing, carts, wishlist, messaging, deposits, inventory, and dashboard workflows.

## Overview

The project does not rely on a heavyweight web framework. Instead, it uses its own request parser, response builder, router, and session handling modules to move a request through the app lifecycle:

`raw HTTP bytes -> request parser -> router -> handler -> template rendering -> HTTP response`

This makes the repository a good fit for learning or extending a custom web stack while still keeping the application split into readable domain modules.

## Features

- Public landing pages, about, contact, terms, and user profile pages.
- Authentication with signup, login, logout, and session-based access control.
- Product browsing, category pages, and filtering.
- Cart, wishlist, deposit, inbox, and conversation flows.
- Dashboard pages for transaction reports, print views, and review submission.
- Inventory-related pages for managing items and item details.
- Jinja2 templates and static assets for server-side rendered UI.
- PostgreSQL connection pooling and reusable query helpers.

## Project Structure

- `core/` - main application logic, page handlers, queries, routes, DB config, and the custom HTTP stack.
- `auth/` - authentication helpers and session management.
- `carts/` - cart routes, handlers, and query helpers.
- `items/` - product detail, category, and filter pages.
- `inventory/` - inventory and item management pages.
- `dashboard/` - transaction reporting and review pages.
- `deposit/` - deposit page and processing flow.
- `messages/` - inbox and conversation handling.
- `wishlist/` - wishlist routes and handlers.
- `sql/` - database schema and seed data.
- `templates/` - HTML templates rendered by the app.
- `static/` - CSS, images, and admin/static assets.

## Tech Stack

- Python 3.13+
- Jinja2 for templating
- psycopg2-binary for PostgreSQL access
- python-dotenv for environment variables
- bcrypt for password hashing
- Pillow for image handling
- google-generativeai for optional AI-related functionality

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

	```bash
	pip install -r requirements.txt
	```

3. Create a `.env` file with the required configuration values:

	```env
	SERVER_HOST=0.0.0.0
	SERVER_PORT=8000
	SECRET_KEY=replace-with-a-secure-value

	DB_HOST=localhost
	DB_PORT=5432
	DB_NAME=online_market_place
	DB_USER=postgres
	DB_PASSWORD=your-password
	```

4. Create the PostgreSQL database and load the schema from `sql/schema.sql`.
5. Optionally seed sample data from `sql/seed.sql`.

## Runtime Notes

- Database settings are loaded from `core/db/config.py`.
- The request/response flow is implemented in `core/http/http_parser.py` and `core/http/response_builder.py`.
- Page handlers in `core/handlers.py` use `template_engine.py` to render HTML from the `templates/` directory.
- The custom router maps HTTP method/path pairs to handler functions through the package-level `routes.py` files.

## Testing

The low-level HTTP stack has a standalone test script at `core/http/test_http.py`. Run it from that directory when you want to validate request parsing and response building.

## Notes

- This repository is structured around a custom server implementation rather than a framework like Django or Flask.
- If you extend the app, keep route definitions, handlers, queries, and templates aligned by feature package so the codebase stays easy to navigate.
- The phase 2 Django API documentation lives in [external_api/README.md](external_api/README.md).
