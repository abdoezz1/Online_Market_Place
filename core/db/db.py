from psycopg2 import pool, extras
from .config import DB_CONFIG

connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    **DB_CONFIG
)

def execute_query(sql, params=None, fetch_one=False, fetch_all=False):
    conn = connection_pool.getconn()
    
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(sql, params)
            conn.commit()
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            
            return None
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        connection_pool.putconn(conn)
        
        
def execute_transaction(queries_list):
    conn = connection_pool.getconn()
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            for sql, params in queries_list:
                cursor.execute(sql, params)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        connection_pool.putconn(conn)