import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voter_mang_sys.settings")
django.setup()

from notifications.routing import websocket_urlpatterns

django_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_app,
    "websocket": URLRouter(websocket_urlpatterns),
})
