from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password, make_password
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterUserMaster
import json

@csrf_exempt
def password_change(request):

    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        # ---------- JWT AUTH ----------
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({
                "status": False,
                "message": "Authorization token missing"
            }, status=401)

        token_str = auth_header.split(" ")[1]

        try:
            token = AccessToken(token_str)
            user_id = token.get("user_id")
        except Exception:
            return JsonResponse({
                "status": False,
                "message": "Invalid or expired token"
            }, status=401)

        try:
            user = VoterUserMaster.objects.get(user_id=user_id)
        except VoterUserMaster.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "User not found"
            }, status=404)

        # ---------- PAYLOAD ----------
        body = json.loads(request.body)

        old_password = body.get("old_password")
        new_password = body.get("new_password")
        confirm_password = body.get("confirm_password")

        # ---------- VALIDATIONS ----------
        if not old_password:
            return JsonResponse({"status": False, "message": "Old password is required"}, status=400)

        if not new_password:
            return JsonResponse({"status": False, "message": "New password is required"}, status=400)

        if not confirm_password:
            return JsonResponse({"status": False, "message": "Confirm password is required"}, status=400)

        if new_password != confirm_password:
            return JsonResponse({
                "status": False,
                "message": "New password and confirm password do not match"
            }, status=400)

        # ---------- CHECK OLD PASSWORD ----------
        if not check_password(old_password, user.password):
            return JsonResponse({
                "status": False,
                "message": "Old password is incorrect"
            }, status=400)

        # ---------- UPDATE PASSWORD ----------
        user.password = make_password(new_password)
        user.save(update_fields=["password"])

        return JsonResponse({
            "status": True,
            "message": "Password changed successfully"
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "status": False,
            "message": "Invalid JSON payload"
        }, status=400)

    except Exception as e:
        return JsonResponse({
            "status": False,
            "error": str(e)
        }, status=500)
