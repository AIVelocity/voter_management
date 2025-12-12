from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from ..models import VoterUserMaster, Roles
import json
import re


def is_valid_mobile(mobile):
    # Allows only exactly 10 digits
    pattern = r'^[6-9]\d{9}$'
    return bool(re.match(pattern, mobile))


@csrf_exempt
def registration(request):

    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "Method must be POST"
        })

    try:
        body = json.loads(request.body)

        first_name = body.get("first_name")
        last_name = body.get("last_name")
        # role_id = body.get("role_id")
        mobile_no = body.get("mobile_no")

        password = body.get("password")
        confirm_password = body.get("confirm_password")

        # ---------- VALIDATION ----------
        if not first_name:
            return JsonResponse({"status": False, "message": "First Name is required"})

        if not last_name:
            return JsonResponse({"status": False, "message": "Last Name is required"})

        # if not role_id:
        #     return JsonResponse({"status": False, "message": "Role is required"})

        if not mobile_no:
            return JsonResponse({"status": False, "message": "Mobile Number is required"})

        if not is_valid_mobile(mobile_no):
            return JsonResponse({
                "status": False,
                "message": "Mobile number must be a valid 10-digit Indian number"
            })

        if not password or not confirm_password:
            return JsonResponse({
                "status": False,
                "message": "Password and Confirm Password are required"
            })

        if password != confirm_password:
            return JsonResponse({
                "status": False,
                "message": "Password and Confirm Password do not match"
            })

        # # ---------- ROLE VALIDATION ----------
        # try:
        #     role = Roles.objects.get(role_id=role_id)
        # except Roles.DoesNotExist:
        #     return JsonResponse({"status": False, "message": "Invalid role_id"})

        # ---------- DUPLICATE MOBILE ----------
        if VoterUserMaster.objects.filter(mobile_no=mobile_no).exists():
            return JsonResponse({
                "status": False,
                "message": "Mobile number already registered"
            })

        # ---------- HASH PASSWORD ----------
        hashed_password = make_password(password)

        # ---------- SAVE USER ----------
        user = VoterUserMaster.objects.create(
            first_name=first_name,
            last_name=last_name,
            mobile_no=mobile_no,
            password=hashed_password,
            confirm_password=hashed_password
            # role=role
        )

        # ---------- RESPONSE ----------
        return JsonResponse({
            "status": True,
            "message": "Registration successful",
            "data": {
                "user_id": user.user_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_no": user.mobile_no
                # "role_id": user.role.role_id
            }
        })

    except Exception as e:
        return JsonResponse({
            "status": False,
            "error": str(e)
        })