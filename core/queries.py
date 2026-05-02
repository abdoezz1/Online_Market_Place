from db import execute_query


# ── User / Auth ──────────────────────────────────────────────────────────────

def get_user_by_id(user_id):
    return execute_query(
        "SELECT * FROM users WHERE id = %s",
        (user_id,), fetch_one=True
    )

def get_user_profile(user_id):
    return execute_query(
        "SELECT * FROM user_profiles WHERE user_id = %s",
        (user_id,), fetch_one=True
    )

def update_user_profile(user_id, phone, address, bio, date_of_birth):
    execute_query(
        """UPDATE user_profiles
           SET phone = %s, address = %s, bio = %s,
               date_of_birth = %s, updated_at = CURRENT_TIMESTAMP
           WHERE user_id = %s""",
        (phone, address, bio, date_of_birth, user_id)
    )

def update_user_names(user_id, first_name, last_name):
    execute_query(
        "UPDATE users SET first_name = %s, last_name = %s WHERE id = %s",
        (first_name, last_name, user_id)
    )

def update_user_password(user_id, hashed_password):
    execute_query(
        "UPDATE users SET password = %s WHERE id = %s",
        (hashed_password, user_id)
    )

def get_user_balance(user_id):
    result = execute_query(
        "SELECT balance FROM user_profiles WHERE user_id = %s",
        (user_id,), fetch_one=True
    )
    return result['balance'] if result else 0


# ── Contact Messages ──────────────────────────────────────────────────────────

def insert_contact_message(name, email, message):
    execute_query(
        "INSERT INTO contact_messages (name, email, message) VALUES (%s, %s, %s)",
        (name, email, message)
    )


# ── User Detail (public profile) ─────────────────────────────────────────────

def get_user_public_profile(profile_id):
    """Return user + profile joined by user_profile.id (not user_id)."""
    return execute_query(
        """SELECT u.username, u.first_name, u.last_name, u.email,
                  up.photo, up.bio, up.address, up.created_at, up.id AS profile_id
           FROM users u
           JOIN user_profiles up ON u.id = up.user_id
           WHERE up.id = %s""",
        (profile_id,), fetch_one=True
    )

def get_user_avg_rating(profile_id):
    """Average rating across all products owned by this profile."""
    result = execute_query(
        """SELECT ROUND(AVG(r.rating), 2) AS avg_rating
           FROM reviews r
           JOIN items i ON r.product_id = i.id
           WHERE i.owned_by_id = %s""",
        (profile_id,), fetch_one=True
    )
    return result['avg_rating'] if result else None

def get_user_for_sale_items(profile_id):
    return execute_query(
        """SELECT i.*, c.name AS category_name
           FROM items i
           JOIN categories c ON i.category_id = c.id
           WHERE i.owned_by_id = %s AND i.for_sale = TRUE""",
        (profile_id,), fetch_all=True
    )


# ── Categories (used by home/filter) ─────────────────────────────────────────

def get_all_categories():
    return execute_query(
        "SELECT * FROM categories ORDER BY name",
        fetch_all=True
    )