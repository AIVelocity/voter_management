import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from datetime import datetime
from .models import Notification

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or getattr(user, "is_anonymous", True):
            # Reject anonymous connections (recommended)
            await self.close(code=4001)
            return

        # Determine groups to join
        self.groups_joined = []
        # per-user
        user_group = f"user_{user.id}"
        await self.channel_layer.group_add(user_group, self.channel_name)
        self.groups_joined.append(user_group)

        # admin group (adjust check as per your user model)
        is_admin = getattr(user, "is_staff", False) or (hasattr(user, "role") and str(getattr(user, "role")).lower() == "admin")
        if is_admin:
            await self.channel_layer.group_add("admins", self.channel_name)
            self.groups_joined.append("admins")

        # agent group (if your user has agent_id attr)
        agent_id = getattr(user, "agent_id", None)
        if agent_id:
            g = f"agent_{agent_id}"
            await self.channel_layer.group_add(g, self.channel_name)
            self.groups_joined.append(g)

        await self.accept()

        # Optionally send unread notifications backlog
        unread = await self._get_unread_notifications_for_user(user.id)
        for n in unread:
            await self.send_json({"event": "notification", "payload": n})

    async def disconnect(self, close_code):
        for g in self.groups_joined:
            try:
                await self.channel_layer.group_discard(g, self.channel_name)
            except Exception:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except Exception:
            return

        typ = data.get("type")
        if typ == "ping":
            await self.send_json({"type": "pong", "time": datetime.now(datetime.timezone.utc).isoformat()})
            return

        if typ == "mark_read":
            notif_id = data.get("id")
            await self._mark_notification_read(notif_id)
            return

        # add other client-sent message handlers here

    # Called by group_send with type='notify'
    async def notify(self, event):
        payload = event.get("payload", {})
        await self.send_json({"event": "notify", "payload": payload})

    @database_sync_to_async
    def _get_unread_notifications_for_user(self, user_id):
        qs = Notification.objects.filter(to_user_id=user_id, is_read=False).values(
            "id", "title", "message", "meta", "created_at"
        )
        return list(qs)

    @database_sync_to_async
    def _mark_notification_read(self, notif_id):
        Notification.objects.filter(id=notif_id).update(is_read=True)
