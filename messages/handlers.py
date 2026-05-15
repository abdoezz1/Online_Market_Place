from template_engine import render_template
from core.http.response_builder import build_response, redirect
from core.auth.session_manager import require_login
from messages import queries


@require_login
def inbox(request):
    user_id = request["user_id"]
    chats = queries.get_conversations(user_id)

    html = render_template("messages/inbox.html", {
        "chats": chats,
        "user": request.get("user")
    })
    return build_response(200, html)


@require_login
def conversation(request):
    from core.queries import get_user_by_id, get_user_profile
    user_id = request["user_id"]
    other_id = request["path_params"]["user_id"]

    msgs = queries.get_messages(user_id, other_id)
    other_user = get_user_by_id(other_id)

    html = render_template("messages/conversation.html", {
        "conversation": msgs,
        "other_user": other_user,
        "other_id": other_id,
        "user": request.get("user"),
        "thread": {},
    })
    return build_response(200, html)


@require_login
def send_message(request):
    sender = request["user_id"]
    receiver = request["form_data"].get("receiver_id")
    content = request["form_data"].get("content")

    queries.send_message(sender, receiver, content)
    return redirect(f"/messages/{receiver}")
