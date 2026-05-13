import psycopg2
from core.db.config import DB_CONFIG

def update_images():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE items SET image = '/static/images/default-product-image.jpg' WHERE image IS NULL OR image = '';")
        conn.commit()
        print(f"Updated {cur.rowcount} items with default image.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_images()
