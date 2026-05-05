routes = [
    ("GET", "/messages", "inbox"),
    ("GET", "/messages/<user_id>", "conversation"),
    ("POST", "/messages/send", "send_message"),
]
