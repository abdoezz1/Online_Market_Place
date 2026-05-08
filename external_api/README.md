# external_api

This folder contains the Django API project used for the phase 2 external API requirements.

## API Reference

The API is built around the shared PostgreSQL schema in `sql/schema.sql` and the Django app in `myapp/`.

### Authentication Model

- Session-authenticated routes expect the `sessionid` cookie returned by `/api/login/`.
- API-key routes expect `X-API-KEY: <key>` or `Authorization: Api-Key <key>`.
- JSON request bodies are accepted for the public API routes.

### Endpoints

#### `POST /api/signup/`

Registers a marketplace user and creates the matching profile row.

Request body:

```json
{
   "username": "alice",
   "email": "alice@example.com",
   "password": "secret123",
   "first_name": "Alice",
   "last_name": "Doe"
}
```

Success response:

```json
{
   "status": "success",
   "message": "User registered successfully.",
   "user": {
      "id": 1,
      "username": "alice",
      "email": "alice@example.com",
      "first_name": "Alice",
      "last_name": "Doe",
      "profile_id": 99
   }
}
```

#### `POST /api/login/`

Authenticates by username or email and returns a session cookie.

Request body:

```json
{
   "identifier": "alice",
   "password": "secret123"
}
```

Success response:

```json
{
   "status": "success",
   "message": "Login successful.",
   "user": {
      "id": 1,
      "username": "alice",
      "email": "alice@example.com",
      "first_name": "Alice",
      "last_name": "Doe"
   }
}
```

The response also sets `sessionid=<value>` as an `HttpOnly` cookie.

#### `POST /deposit/process-payment/`

Processes a deposit for the signed-in user.

Required headers:

- `Cookie: sessionid=<value>`

Request body:

```json
{
   "amount": "25.50",
   "card_number": "4111111111111111",
   "cvc": "123"
}
```

Validation rules:

- Amount must be between 10 and 10,000.
- Card number must be exactly 16 digits and start with `4` or `5`.
- CVC must be exactly 3 digits.
- A user may submit at most 3 deposits per day.

#### `GET /external_api/api/products/`

Lists products marked as advertised in the shared SQL schema.

Required headers:

- `X-API-KEY: <key>` or `Authorization: Api-Key <key>`

Success response shape:

```json
{
   "status": "success",
   "client": {
      "id": 1,
      "name": "Test Client"
   },
   "count": 1,
   "products": []
}
```

#### `POST /external_api/api/create_order/`

Creates an order for an external client.

Required headers:

- `X-API-KEY: <key>` or `Authorization: Api-Key <key>`

Request body:

```json
{
   "buyer_id": 4,
   "product_id": 1,
   "quantity": 1
}
```

#### `POST /inventory/upload/`

Imports CSV rows into the `items` table for the currently signed-in seller.

Required headers:

- `Cookie: sessionid=<value>`

Upload field:

- `file` or `csv_file`

Supported CSV columns include `name`, `price`, `quantity`, `category`, `category_id`, `description`, `advertise`, and `for_sale`.

#### `POST /inventory/ai-desc/`

Generates a product description for the current session user.

Required headers:

- `Cookie: sessionid=<value>`

Request body:

```json
{
   "name": "Demo Item",
   "category": "Accessories",
   "features": "Lightweight, durable, and easy to carry",
   "tone": "friendly and persuasive"
}
```

If `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set, the service uses Gemini; otherwise it falls back to a local description generator.

## Setup

1. Make sure your PostgreSQL database is running and matches the values in `.env`.
2. Activate the virtual environment used by this workspace.
3. Install dependencies if needed:

   ```bash
   pip install -r requirements.txt
   ```

4. Apply the repository SQL schema from the root `sql/` folder:

   ```bash
   psql -h localhost -p 5433 -U postgres -d online_market_place -f ..\sql\schema.sql
   ```

5. Optionally load seed data from the same folder:

   ```bash
   psql -h localhost -p 5433 -U postgres -d online_market_place -f ..\sql\seed.sql
   ```

6. Create a superuser if you need admin access to the Django admin site:

   ```bash
   python manage.py createsuperuser
   ```

## Run

Start the development server on port 8001:

```bash
python manage.py runserver 0.0.0.0:8001
```

## Verified Endpoints

- `/api/signup/` registers a marketplace user.
- `/api/login/` returns a `sessionid` cookie for session-authenticated routes.
- `/deposit/process-payment/` processes a deposit for the signed-in user.
- `/external_api/api/products/` lists advertised products when given an API key.
- `/external_api/api/create_order/` creates an order when given an API key.
- `/inventory/upload/` imports CSV rows into `items` for the current session.
- `/inventory/ai-desc/` generates a product description for the current session.
- `/` returns a simple landing response.
- `/health/` returns JSON: `{ "status": "ok" }`.
- `/admin/` is available through Django admin.

## Notes

- The project currently uses `myproject/urls.py` to include `myapp.urls`.
- The marketplace data model is managed from the repository `sql/` folder rather than Django app migrations.
- Send the API key in `X-API-KEY` or `Authorization: Api-Key <key>` for the advertised-products and create-order endpoints.
- The session-authenticated endpoints expect the `sessionid` cookie returned by `/api/login/`.
- The endpoint behavior is covered by Django tests in `myapp/tests.py`.
- If you add phase 2 API endpoints later, register them in `myapp/urls.py` and implement the corresponding views in `myapp/views.py`.