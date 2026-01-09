from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs
from application.models import VoterUserMaster
from logger import logger

@database_sync_to_async
def get_user_from_token(token):
    try:
        # Decode the token you provided
        access_token = AccessToken(token)
        
        # Your token payload has "user_id": "2"
        user_id = access_token.get("user_id")
        
        if not user_id:
            return AnonymousUser()
            
        # Look up your VoterUserMaster
        return VoterUserMaster.objects.select_related('role').get(user_id=user_id)
    except Exception as e:
        logger.error(f"JWTAuthMiddleware: Failed to authenticate token. Error: {e}")
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
        # Get token from query string: ws://.../?token=eyJhbGci...
            print("--- WebSocket Middleware Start ---")
            logger.info("WebSocket Middleware: New connection attempt.")
            query_string = scope.get("query_string", b"").decode("utf-8")
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]
            print(f"Token found: {token[:10] if token else 'None'}...")
            logger.info(f"WebSocket Middleware: Token found: {token[:10] if token else 'None'}...")

            if token:
                user = await get_user_from_token(token)
                scope["user"] = user
                print(f"User assigned to scope: {user}")
            else:
                scope["user"] = AnonymousUser()
                print("No token, assigned AnonymousUser")
        except Exception as e:
            print(f"CRITICAL MIDDLEWARE ERROR: {e}") # This will catch the 500 error
            scope["user"] = AnonymousUser()
        return await self.app(scope, receive, send)