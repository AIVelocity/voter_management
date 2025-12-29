import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from notifications.routing import websocket_urlpatterns
from voter_mang_sys.channel_jwt_middleware import JWTAuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voter_mang_sys.settings")

django_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
