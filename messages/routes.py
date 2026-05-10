from messages.handlers import inbox
from messages.handlers import conversation
from messages.handlers import send_message

routes = [
    ("GET", "/messages", inbox),
    ("GET", "/messages/<user_id>", conversation),
    ("POST", "/messages/send", send_message),
]
