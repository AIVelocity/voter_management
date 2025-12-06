from django.urls import path
from .views.send_message_view import send_template, send_text
from .views.webhook_view import verify_webhook, receive_webhook

urlpatterns = [
    path("sendTemplate/", send_template),
    path("sendText/", send_text),
    path("webhook/", verify_webhook, name="whatsapp_verify"),
    path("webhook", receive_webhook, name="whatsapp_webhook"),
]
