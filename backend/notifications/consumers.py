import json
import time # Added for rate limiting
from datetime import datetime, timezone
from django.core.serializers.json import DjangoJSONEncoder
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification
from logger import logger
import asyncio

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.groups_joined = []
        self.last_pong_time = 0  # To track ping frequency

        if not self.user or self.user.is_anonymous:
            await self.close(code=4003)
            return

        # 1. Join User Group
        self.user_group = f"user_{self.user.user_id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        self.groups_joined.append(self.user_group)

        # 2. Join Admin Group (Fixed potential DB error)
        is_admin = await self._check_if_admin()
        if is_admin:
            await self.channel_layer.group_add("admins", self.channel_name)
            self.groups_joined.append("admins")

        await self.accept()
        logger.info(f"WebSocket: User {self.user.user_id} connected.")

        # 3. Initial Sync
        unread_data = await self._get_unread_notifications()
        if unread_data:
            await self.send(text_data=json.dumps({
                "event": "initial_sync",
                "payload": unread_data
            }, cls=DjangoJSONEncoder))

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "ping":
                current_time = time.time()
                # Only respond if 5 seconds have passed (Rate Limiting)
                # This prevents high frequency without blocking other messages
                if current_time - self.last_pong_time > 5:
                    self.last_pong_time = current_time
                    await self.send(text_data=json.dumps({
                        "type": "pong", 
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }, cls=DjangoJSONEncoder))
            
            elif msg_type == "mark_read":
                notif_id = data.get("id")
                if notif_id:
                    await self._mark_notification_read(notif_id)

        except Exception as e:
            logger.error(f"WebSocket Receive Error: {e}")

    async def disconnect(self, close_code):
        for group in self.groups_joined:
            try:
                await self.channel_layer.group_discard(group, self.channel_name)
            except Exception:
                pass
        logger.info(f"WebSocket disconnected for user.")

    async def notify(self, event):
        await self.send(text_data=json.dumps({
            "event": "notify",
            "payload": event.get("payload", {})
        }, cls=DjangoJSONEncoder))

    # --- Database Methods ---

    @database_sync_to_async
    def _check_if_admin(self):
        """Safely check roles in a sync context"""
        try:
            return self.user.role.role_name.lower() == "admin"
        except Exception:
            return False

    @database_sync_to_async
    def _get_unread_notifications(self):
        return list(
            Notification.objects.filter(to_user_id=self.user.user_id, is_read=False)
            .values("id", "title", "message", "meta", "created_at")
        )

    @database_sync_to_async
    def _mark_notification_read(self, notif_id):
        Notification.objects.filter(id=notif_id, to_user_id=self.user.user_id).update(is_read=True)