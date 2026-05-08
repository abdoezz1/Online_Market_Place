from __future__ import annotations

import csv
import io
import os
import uuid
import warnings
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import bcrypt
from dotenv import load_dotenv
from django.utils import timezone
from psycopg2 import extras, pool

try:
    from google import genai as genai  # type: ignore
except ImportError:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai  # type: ignore


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)


def _db_config() -> Dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }


_POOL: Optional[pool.ThreadedConnectionPool] = None


def get_pool() -> pool.ThreadedConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = pool.ThreadedConnectionPool(minconn=1, maxconn=10, **_db_config())
    return _POOL


def execute_query(
    sql: str,
    params: Optional[tuple[Any, ...]] = None,
    *,
    fetch_one: bool = False,
    fetch_all: bool = False,
) -> Any:
    connection_pool = get_pool()
    connection = connection_pool.getconn()
    try:
        with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(sql, params or ())
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            connection.commit()
            return None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection_pool.putconn(connection)


def execute_transaction(callback: Callable[[extras.RealDictCursor], Any]) -> Any:
    connection_pool = get_pool()
    connection = connection_pool.getconn()
    try:
        with connection:
            with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                return callback(cursor)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection_pool.putconn(connection)


def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_user(
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> Dict[str, Any]:
    duplicate = execute_query(
        "SELECT id FROM users WHERE username = %s OR email = %s",
        (username, email),
        fetch_one=True,
    )
    if duplicate:
        raise ValueError("Username or email already exists.")

    password_hash = hash_password(password)

    def _create(cursor: extras.RealDictCursor) -> Dict[str, Any]:
        cursor.execute(
            """
            INSERT INTO users (username, email, password, first_name, last_name)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, username, email, first_name, last_name
            """,
            (username, email, password_hash, first_name, last_name),
        )
        user = cursor.fetchone()

        cursor.execute(
            """
            INSERT INTO user_profiles (user_id)
            VALUES (%s)
            RETURNING id
            """,
            (user["id"],),
        )
        profile = cursor.fetchone()
        user["profile_id"] = profile["id"]
        return user

    return execute_transaction(_create)


def authenticate_user(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    user = execute_query(
        """
        SELECT id, username, email, password, first_name, last_name
        FROM users
        WHERE username = %s OR email = %s
        """,
        (identifier, identifier),
        fetch_one=True,
    )
    if not user or not verify_password(password, user["password"]):
        return None
    user.pop("password", None)
    return user


def create_session(user_id: int) -> str:
    session_key = uuid.uuid4().hex
    expires_at = timezone.now() + timedelta(days=7)
    execute_query(
        """
        INSERT INTO sessions (session_key, user_id, expires_at)
        VALUES (%s, %s, %s)
        """,
        (session_key, user_id, expires_at),
    )
    return session_key


def get_session_user_id(session_key: str) -> Optional[int]:
    row = execute_query(
        """
        SELECT user_id
        FROM sessions
        WHERE session_key = %s AND expires_at > NOW()
        """,
        (session_key,),
        fetch_one=True,
    )
    return row["user_id"] if row else None


def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    return execute_query(
        "SELECT * FROM user_profiles WHERE user_id = %s",
        (user_id,),
        fetch_one=True,
    )


def get_api_client(api_key: str) -> Optional[Dict[str, Any]]:
    return execute_query(
        """
        SELECT *
        FROM api_clients
        WHERE api_key = %s AND is_active = TRUE
        """,
        (api_key,),
        fetch_one=True,
    )


def list_advertised_products() -> List[Dict[str, Any]]:
    rows = execute_query(
        """
        SELECT
            i.id,
            i.name,
            i.price,
            i.description,
            i.image,
            i.quantity,
            i.average_rating,
            i.view_count,
            i.for_sale,
            i.advertise,
            i.created_at,
            c.name AS category_name,
            u.username AS owner_username
        FROM items i
        LEFT JOIN categories c ON c.id = i.category_id
        LEFT JOIN user_profiles up ON up.id = i.owned_by_id
        LEFT JOIN users u ON u.id = up.user_id
        WHERE i.advertise = TRUE
        ORDER BY i.created_at DESC, i.id DESC
        """,
        fetch_all=True,
    )
    return rows or []


def create_order(
    buyer_id: int,
    product_id: int,
    quantity: int,
) -> Dict[str, Any]:
    item = execute_query(
        """
        SELECT id, quantity, price, owned_by_id, for_sale, name
        FROM items
        WHERE id = %s
        """,
        (product_id,),
        fetch_one=True,
    )
    if not item:
        raise ValueError("Product not found.")
    if not item["for_sale"]:
        raise ValueError("Product is not available for sale.")
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")
    if item["quantity"] < quantity:
        raise ValueError("Insufficient stock.")
    if not item["owned_by_id"]:
        raise ValueError("Seller profile is missing for this item.")

    seller_id = item["owned_by_id"]

    def _create(cursor: extras.RealDictCursor) -> Dict[str, Any]:
        cursor.execute(
            """
            INSERT INTO orders (buyer_id, seller_id, product_id, quantity)
            VALUES (%s, %s, %s, %s)
            RETURNING id, buyer_id, seller_id, product_id, quantity
            """,
            (buyer_id, seller_id, product_id, quantity),
        )
        order = cursor.fetchone()
        order["product_name"] = item["name"]
        order["unit_price"] = item["price"]
        return order

    return execute_transaction(_create)


def process_deposit(user_id: int, amount: Decimal) -> Dict[str, Any]:
    profile = get_user_profile(user_id)
    if not profile:
        raise ValueError("User profile not found.")

    today_count = execute_query(
        """
        SELECT COUNT(*) AS total
        FROM deposits
        WHERE user_id = %s AND DATE(date) = CURRENT_DATE
        """,
        (profile["id"],),
        fetch_one=True,
    )
    if today_count and int(today_count["total"]) >= 3:
        raise ValueError("Daily deposit limit reached.")

    def _create(cursor: extras.RealDictCursor) -> Dict[str, Any]:
        cursor.execute(
            """
            INSERT INTO deposits (amount, status, user_id)
            VALUES (%s, %s, %s)
            RETURNING id, amount, status, date
            """,
            (amount, "completed", profile["id"]),
        )
        deposit = cursor.fetchone()

        cursor.execute(
            """
            UPDATE user_profiles
            SET balance = balance + %s, updated_at = NOW()
            WHERE id = %s
            RETURNING balance
            """,
            (amount, profile["id"]),
        )
        balance_row = cursor.fetchone()
        deposit["balance"] = balance_row["balance"] if balance_row else profile["balance"]
        return deposit

    return execute_transaction(_create)


def _category_id_from_value(category_value: Optional[str]) -> Optional[int]:
    if not category_value:
        return None
    category_value = str(category_value).strip()
    if not category_value:
        return None
    if category_value.isdigit():
        category = execute_query(
            "SELECT id FROM categories WHERE id = %s",
            (int(category_value),),
            fetch_one=True,
        )
        return category["id"] if category else None

    existing = execute_query(
        "SELECT id FROM categories WHERE LOWER(name) = LOWER(%s)",
        (category_value,),
        fetch_one=True,
    )
    if existing:
        return existing["id"]

    created = execute_query(
        "INSERT INTO categories (name) VALUES (%s) RETURNING id",
        (category_value,),
        fetch_one=True,
    )
    return created["id"] if created else None


def bulk_upload_items(user_id: int, uploaded_file: Any) -> Dict[str, Any]:
    profile = get_user_profile(user_id)
    if not profile:
        raise ValueError("User profile not found.")

    raw_content = uploaded_file.read()
    if isinstance(raw_content, bytes):
        csv_text = raw_content.decode("utf-8-sig")
    else:
        csv_text = str(raw_content)

    reader = csv.DictReader(io.StringIO(csv_text))
    inserted_rows: List[Dict[str, Any]] = []

    def _create(cursor: extras.RealDictCursor) -> Dict[str, Any]:
        for row in reader:
            name = (row.get("name") or row.get("title") or "").strip()
            if not name:
                continue

            price_value = row.get("price") or "0"
            try:
                price = Decimal(str(price_value).strip())
            except (InvalidOperation, ValueError):
                price = Decimal("0.00")

            quantity_value = row.get("quantity") or row.get("qty") or "0"
            try:
                quantity = int(quantity_value)
            except (TypeError, ValueError):
                quantity = 0

            category_id = _category_id_from_value(row.get("category_id") or row.get("category"))
            description = (row.get("description") or "").strip() or None
            image = (row.get("image") or "").strip() or None
            for_sale = str(row.get("for_sale", "true")).strip().lower() in {"1", "true", "yes", "y", "on"}
            advertise = str(row.get("advertise", "false")).strip().lower() in {"1", "true", "yes", "y", "on"}

            cursor.execute(
                """
                INSERT INTO items (
                    name, price, description, image, quantity, for_sale,
                    available_stock, advertise, quantity_advertise, owned_by_id, category_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, price
                """,
                (
                    name,
                    price,
                    description,
                    image,
                    quantity,
                    for_sale,
                    quantity,
                    advertise,
                    quantity,
                    profile["id"],
                    category_id,
                ),
            )
            inserted_rows.append(cursor.fetchone())

        return {"inserted": inserted_rows}

    result = execute_transaction(_create)
    return {"count": len(inserted_rows), "items": result["inserted"]}


def generate_description(name: str, category: str = "", features: str = "", tone: str = "") -> tuple[str, str]:
    prompt = (
        f"Write a concise marketplace product description for '{name}'. "
        f"Category: {category or 'unspecified'}. "
        f"Features: {features or 'none provided'}. "
        f"Tone: {tone or 'clear and persuasive'}."
    )

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            if hasattr(genai, "Client"):
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                )
            else:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
            text = getattr(response, "text", "") or ""
            if text.strip():
                return text.strip(), "gemini"
        except Exception:
            pass

    fallback_bits = [name.strip() or "This item"]
    if category.strip():
        fallback_bits.append(f"in the {category.strip()} category")
    if features.strip():
        fallback_bits.append(f"featuring {features.strip()}")
    fallback = " ".join(fallback_bits)
    return (
        f"{fallback}. It is listed for buyers looking for a practical, well-presented product.",
        "fallback",
    )