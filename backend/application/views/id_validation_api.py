from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterUserMaster
import json


@csrf_exempt
def id_validation(request):

    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        body = json.loads(request.body)

        mobile_no = body.get("mobile_no")
        password = body.get("password")

        # -------- VALIDATIONS --------
        if not mobile_no:
            return JsonResponse({"status": False, "message": "Mobile number is required"}, status=400)
        if not password:
            return JsonResponse({"status": False, "message": "Password is required"}, status=400)

        # -------- FIND USER --------
        user = VoterUserMaster.objects.filter(mobile_no=mobile_no).select_related("role").first()

        if not user:
            return JsonResponse({"status": False, "message": "User not found"}, status=404)

        # -------- PASSWORD CHECK --------
        if not check_password(password, user.password):
            return JsonResponse({"status": False, "message": "Invalid mobile number or password"}, status=401)

        # -------- GENERATE ACCESS TOKEN ONLY --------
        access_token = str(AccessToken.for_user(user))

        # -------- USER NAME --------
        first = user.first_name.capitalize() if user.first_name else ""
        last = user.last_name.capitalize() if user.last_name else ""
        user_name = f"{first} {last}".strip()

        # -------- SUCCESS --------
        return JsonResponse({
            "status": True,
            "access_token": access_token,
            "token_type": "Bearer",
            # "expires_in_minutes": 60,
            "user_id": user.user_id,
            "role": user.role.role_name if hasattr(user.role, "role_name") else user.role.role_id,
            "user_name": user_name,
            "message": "Login successful"
        })

    except json.JSONDecodeError:
        return JsonResponse({"status": False, "message": "Invalid JSON"}, status=400)

    except Exception as e:
        return JsonResponse({"status": False, "message": str(e)}, status=500)
