from django.urls import path
from .views.send_message_view import send_template, send_text, get_messages_for_voter, get_all_templates, send_image, send_audio, send_document, send_video
from .views.webhook_view import whatsapp_webhook
from .views.media_upload_view import upload_media

urlpatterns = [
    path("sendTemplate/", send_template),
    path("sendText/", send_text),
    path("getMessagesForVoter/", get_messages_for_voter),
    path("templates/", get_all_templates),
    path("webhook/", whatsapp_webhook, name="whatsapp_webhook"),
    path("send/image/", send_image, name="send_image"),
    path("send/audio/", send_audio, name="send_audio"),
    path("send/document/", send_document, name="send_document"),
    path("send/video/", send_video, name="send_video"),
    path("upload/media/", upload_media, name="upload_media"),
]
