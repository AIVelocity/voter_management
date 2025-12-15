from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification

def _make_payload(notif):
    return {
        "id": notif.id,
        "title": notif.title,
        "message": notif.message,
        "meta": notif.meta or {},
        "created_at": notif.created_at.isoformat()
    }

def broadcast_to_admins(title, message, meta=None):
    notif = Notification.objects.create(title=title, message=message, to_role="admin", meta=meta or {})
    payload = _make_payload(notif)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "admins",
        {"type": "notify", "payload": payload}
    )
    return notif

def broadcast_to_agent(agent_id, title, message, meta=None):
    notif = Notification.objects.create(title=title, message=message, to_agent=agent_id, meta=meta or {})
    payload = _make_payload(notif)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"agent_{agent_id}",
        {"type": "notify", "payload": payload}
    )
    return notif

def send_to_user(user_id, title, message, meta=None):
    notif = Notification.objects.create(title=title, message=message, to_user_id=user_id, meta=meta or {})
    payload = _make_payload(notif)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {"type": "notify", "payload": payload}
    )
    return notif
