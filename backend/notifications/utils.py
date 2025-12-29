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


# -------------------------------
# 1️⃣ SEND NOTIFICATION TO ADMINS
# -------------------------------
def broadcast_to_admins(title, message, meta=None):
    notif = Notification.objects.create(
        title=title,
        message=message,
        to_role="admin",     # Your Notification model stores string roles
        meta=meta or {}
    )

    payload = _make_payload(notif)
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "admins",            # Your consumer subscribes admin users to this group
        {"type": "notify", "payload": payload}
    )

    return notif


# -------------------------------
# 2️⃣ SEND NOTIFICATION TO A SINGLE USER
# -------------------------------
def send_to_user(user_id, title, message, meta=None):
    notif = Notification.objects.create(
        title=title,
        message=message,
        to_user_id=user_id,   # Your Notification table has to_user_id field
        meta=meta or {}
    )

    payload = _make_payload(notif)
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",   # Consumer subscribes users to this group
        {"type": "notify", "payload": payload}
    )

    return notif
