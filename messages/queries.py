from db import execute_query


def get_conversations(user_id):
    sql = """
    SELECT DISTINCT 
        CASE 
            WHEN sender_id = %s THEN receiver_id
            ELSE sender_id
        END as user_id
    FROM messages
    WHERE sender_id = %s OR receiver_id = %s
    """
    return execute_query(sql, (user_id, user_id, user_id), fetch_all=True)


def get_messages(user1, user2):
    sql = """
    SELECT *
    FROM messages
    WHERE (sender_id=%s AND receiver_id=%s)
       OR (sender_id=%s AND receiver_id=%s)
    ORDER BY created_at ASC
    """
    return execute_query(sql, (user1, user2, user2, user1), fetch_all=True)


def send_message(sender, receiver, content):
    sql = """
    INSERT INTO messages (sender_id, receiver_id, content)
    VALUES (%s,%s,%s)
    """
    execute_query(sql, (sender, receiver, content))
