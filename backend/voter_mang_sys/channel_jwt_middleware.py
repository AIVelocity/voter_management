import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

User = get_user_model()

@database_sync_to_async
def get_user_from_jwt(payload):
    """
    Convert decoded JWT payload → actual Django user.
    """
    try:
        user_id = payload.get("user_id")
        return User.objects.get(user_id=user_id)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)

        token = None
        if "token" in query_params:
            token = query_params["token"][0]

        # Default anonymous user
        scope["user"] = AnonymousUser()

        if token:
            try:
                payload = jwt.decode(
                    token,
                    settings.SIMPLE_JWT["SIGNING_KEY"],
                    algorithms=[settings.SIMPLE_JWT.get("ALGORITHM", "HS256")]
                )

                scope["user"] = await get_user_from_jwt(payload)

            except Exception:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
