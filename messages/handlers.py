from template_engine import render_template
from response_builder import build_response, redirect
from session_manager import require_login
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
    user_id = request["user_id"]
    other_id = request["path_params"]["user_id"]

    messages = queries.get_messages(user_id, other_id)

    html = render_template("messages/conversation.html", {
        "messages": messages,
        "other_id": other_id,
        "user": request.get("user")
    })
    return build_response(200, html)


@require_login
def send_message(request):
    sender = request["user_id"]
    receiver = request["form_data"].get("receiver_id")
    content = request["form_data"].get("content")

    queries.send_message(sender, receiver, content)
    return redirect(f"/messages/{receiver}")
