from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password, make_password
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterUserMaster
import json
from logger import logger
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def password_change(request):

    try:
        logger.info("change_password_api: Change password request received")
        # ---------- JWT AUTH ----------
        user = request.user
        # ---------- PAYLOAD ----------
        body = request.data

        old_password = body.get("old_password")
        new_password = body.get("new_password")
        confirm_password = body.get("confirm_password")

        # ---------- VALIDATIONS ----------
        if not old_password:
            return Response({"status": False, "message": "Old password is required"}, status=400)

        if not new_password:
            return Response({"status": False, "message": "New password is required"}, status=400)

        if not confirm_password:
            return Response({"status": False, "message": "Confirm password is required"}, status=400)

        if new_password != confirm_password:
            return Response({
                "status": False,
                "message": "New password and confirm password do not match"
            }, status=400)

        # ---------- CHECK OLD PASSWORD ----------
        if not check_password(old_password, user.password):
            return Response({
                "status": False,
                "message": "Old password is incorrect"
            }, status=400)

        # ---------- UPDATE PASSWORD ----------
        user.password = make_password(new_password)
        user.save(update_fields=["password"])
        logger.info("change_password_api: Password changed successfully")

        return Response({
            "status": True,
            "message": "Password changed successfully"
        })

    except json.JSONDecodeError:
        return Response({
            "status": False,
            "message": "Invalid JSON payload"
        }, status=400)

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)
