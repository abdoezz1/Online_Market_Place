"""
auth.py: Authentication
Handles password hashing, user registration, and login verification.
"""
import bcrypt
from core.db import db  

# ─────────────────────────────────────────────
#  Password Utilities
# ─────────────────────────────────────────────

def hash_password(plain_text: str) -> str:
    """
    Hash a plain-text password using bcrypt with an auto-generated salt.
    Returns the hash as a UTF-8 string for storage in the DB.
    """
    password_bytes = plain_text.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_text: str, hashed: str) -> bool:
    """
    Check a plain-text password against a stored bcrypt hash.
    Returns True if they match, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_text.encode("utf-8"),
            hashed.encode("utf-8")
        )
    except Exception:
        return False


# ─────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────

def register_user(
    username: str,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = ""
) -> dict:
    """
    Register a new user.

    Steps:
      1. Validate that username and email are not already taken.
      2. Hash the password.
      3. INSERT into `users` table.
      4. INSERT into `user_profiles` table (auto-created with default balance=1000).

    Returns:
      {"success": True,  "user_id": <int>}           on success
      {"success": False, "error": "<reason>"}         on failure
    """
    # Check uniqueness of username and email
    existing = db.execute_query(
        "SELECT id FROM users WHERE username = %s OR email = %s LIMIT 1",
        (username, email),
        fetch_one=True
    )
    if existing:
        # Determine which field is duplicated for a helpful error message
        by_username = db.execute_query(
            "SELECT id FROM users WHERE username = %s LIMIT 1",
            (username,),
            fetch_one=True
        )
        if by_username:
            return {"success": False, "error": "Username already taken."}
        return {"success": False, "error": "Email already registered."}

    # Hash the password
    hashed_pw = hash_password(password)

    # Insert into users
    user_row = db.execute_query(
        """
        INSERT INTO users (username, email, password, first_name, last_name,
                           is_staff, is_active, date_joined)
        VALUES (%s, %s, %s, %s, %s, FALSE, TRUE, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        (username, email, hashed_pw, first_name, last_name),
        fetch_one=True
    )

    if not user_row:
        return {"success": False, "error": "Failed to create user account."}

    user_id = user_row["id"]

    # insert into user_profiles
    profile_row = db.execute_query(
        """
        INSERT INTO user_profiles (user_id, balance, created_at, updated_at)
        VALUES (%s, 1000, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        (user_id,),
        fetch_one=True
    )

    if not profile_row:
        # Profile creation failed — clean up the user row to avoid orphaned records
        db.execute_query("DELETE FROM users WHERE id = %s", (user_id,))
        return {"success": False, "error": "Failed to create user profile."}

    return {"success": True, "user_id": user_id}


# ─────────────────────────────────────────────
#  Authentication
# ─────────────────────────────────────────────

def authenticate(identifier: str, password: str):
    """
    Verify login credentials. Accepts either a username OR an email address.

    Returns:
      user_id (int)  — on successful authentication
      None           — on failure (wrong credentials or inactive account)
    """
    # Look up by username first, then by email
    user = db.execute_query(
        """
        SELECT id, password, is_active
        FROM users
        WHERE username = %s OR email = %s
        LIMIT 1
        """,
        (identifier, identifier),
        fetch_one=True
    )

    if not user:
        return None  # No such user

    if not user["is_active"]:
        return None  # Account is disabled

    if not verify_password(password, user["password"]):
        return None  # Wrong password

    return user["id"]
