from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterUserMaster, VoterList
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from logger import logger
from rest_framework.decorators import throttle_classes
from .rate_limiter import LoginRateThrottle

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def id_validation(request):

    try:
        body = request.data
        logger.info("id_validation_api: ID validation request received")
        mobile_no = (body.get("mobile_no") or "").strip()
        password = (body.get("password") or "").strip()

        # -------- VALIDATIONS --------
        if not mobile_no:
            return Response({"status": False, "message": "Mobile number is required"}, status=400)
        if not password:
            return Response({"status": False, "message": "Password is required"}, status=400)

        # -------- FIND USER --------
        user = VoterUserMaster.objects.filter(mobile_no=mobile_no).select_related("role").first()

        if not user:
            return Response({"status": False, "message": "User not found"}, status=404)

        # -------- PASSWORD CHECK --------
        if not check_password(password, user.password):
            return Response({"status": False, "message": "Invalid mobile number or password"}, status=401)

        # -------- GENERATE ACCESS TOKEN --------
        access_token = str(AccessToken.for_user(user))

        # -------- USER NAME --------
        first = (user.first_name or "").capitalize()
        last = (user.last_name or "").capitalize()
        user_name = f"{first} {last}".strip()

        # -------- ROLE (SAFE HANDLING) --------
        if user.role:
            role_name = user.role.role_name
            role_id = user.role.role_id
        else:
            role_name = None
            role_id = None

        logger.info(f"id_validation_api: User {user.user_id} authenticated successfully")    
        # -------- SUCCESS --------
        return Response({
            "status": True,
            "access_token": access_token,
            "token_type": "Bearer",
            "user_id": user.user_id,
            "assigned": True if VoterList.objects.filter(user_id=user.user_id).exists() else False,
            "user_name": user_name,
            "role_id": role_id,
            "role_name": role_name,
            "message": "Login successful",
            # "permissions": permissions
        })

    except json.JSONDecodeError:
        return Response({"status": False, "message": "Invalid JSON"}, status=400)

    except Exception as e:
        return Response({"status": False, "message": str(e)}, status=500)
