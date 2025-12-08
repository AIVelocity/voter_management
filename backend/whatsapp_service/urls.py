from django.urls import path
from .views.send_message_view import send_template, send_text, get_messages_for_voter, get_all_templates
from .views.webhook_view import verify_webhook, receive_webhook

urlpatterns = [
    path("sendTemplate/", send_template),
    path("sendText/", send_text),
    path("getMessagesForVoter/", get_messages_for_voter),
    path("templates/", get_all_templates),
    path("webhook/", verify_webhook, name="whatsapp_verify"),
    path("webhook", receive_webhook, name="whatsapp_webhook"),
]
