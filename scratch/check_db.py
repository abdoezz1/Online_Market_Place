import psycopg2
from core.db.config import DB_CONFIG

def check_users():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT username, password FROM users;")
        rows = cur.fetchall()
        for row in rows:
            print(f"Username: {row[0]}, Password: {row[1]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()
