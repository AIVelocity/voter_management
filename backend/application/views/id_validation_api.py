from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password
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
            return JsonResponse({
                "status": False,
                "message": "Mobile number is required"
            })

        if not password:
            return JsonResponse({
                "status": False,
                "message": "Password is required"
            })

        # -------- FIND USER BY MOBILE --------
        user = VoterUserMaster.objects.filter(mobile_no=mobile_no).select_related("role").first()

        if not user:
            return JsonResponse({
                "status": False,
                "message": "User not found"
            }, status=404)

        # -------- PASSWORD CHECK --------
        if not check_password(password, user.password):
            return JsonResponse({
                "status": False,
                "message": "Invalid mobile number or password"
            }, status=401)

        # -------- SUCCESS --------
        return JsonResponse({
            "status": True,
            "role": user.role.role_name if hasattr(user.role, "role_name") else user.role.role_id,
            "user_name": f"{user.first_name} {user.last_name}",
            "user_id": user.user_id,
            "message": "Login successful"
        })

    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": str(e)
        }, status=500)
