import json
from datetime import datetime, timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()


        self.user = user
        self.groups_joined = []

        # -------------------------------
        # 1️⃣ Per-user group
        # -------------------------------
        user_group = f"user_{user.user_id}"
        await self.channel_layer.group_add(user_group, self.channel_name)
        self.groups_joined.append(user_group)

        # -------------------------------
        # 2️⃣ Admin group
        # -------------------------------
        role_name = getattr(getattr(user, "role", None), "role_name", "").lower()

        if role_name == "admin":
            await self.channel_layer.group_add("admins", self.channel_name)
            self.groups_joined.append("admins")

        await self.accept()

        # Send unread notifications
        unread = await self._get_unread_notifications(user.user_id)
        for n in unread:
            await self.send_json({
                "event": "notification",
                "payload": n
            })

    async def disconnect(self, close_code):
        for group in self.groups_joined:
            try:
                await self.channel_layer.group_discard(group, self.channel_name)
            except:
                pass

    async def receive(self, text_data=None, bytes_data=None):

        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except:
            return

        msg_type = data.get("type")

        # Client heartbeat
        if msg_type == "ping":
            await self.send_json({
                "type": "pong",
                "time": datetime.now(timezone.utc).isoformat()
            })
            return

        # Mark notification read
        if msg_type == "mark_read":
            notif_id = data.get("id")
            await self._mark_notification_read(notif_id)
            return

    # Called by group_send
    async def notify(self, event):
        payload = event.get("payload", {})
        await self.send_json({
            "event": "notify",
            "payload": payload
        })

    @database_sync_to_async
    def _get_unread_notifications(self, user_id):
        return list(
            Notification.objects.filter(
                to_user_id=user_id,
                is_read=False
            ).values("id", "title", "message", "meta", "created_at")
        )

    @database_sync_to_async
    def _mark_notification_read(self, notif_id):
        Notification.objects.filter(id=notif_id).update(is_read=True)
