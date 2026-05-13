import psycopg2
from core.db.config import DB_CONFIG

updates = [
    ("ahmed_m", "$2b$12$rZ5OkHi0qBxvcB3bpN.RhuFCvDRa.LAWLxwZ9bbonbZnSF69urCra"),
    ("sara_k", "$2b$12$QBElWtENFhbEw19LJqL8CeU9i/qMBj4.ffgxKxaZQd.LFzCqaBYAa"),
    ("omar_h", "$2b$12$FyTRPqnbylQ11sm0y1pC0uy8TTchkp1W9LJ3uEP8p66eB4L45SzO6"),
    ("admin", "$2b$12$DQ7xyChMz0b/68u8xg9bQu1TdKliey.c865cMH6x7/T9rnDgVIlla"),
    ("nour_a", "$2b$12$bSNGV4DLFl9nF2H4htVHI.q5MXet0YsmS92N7vgrtmAfa1b.WiPjq")
]

def update_users():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        for username, hashed in updates:
            cur.execute("UPDATE users SET password = %s WHERE username = %s;", (hashed, username))
        conn.commit()
        print("Updated users successfully.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_users()
