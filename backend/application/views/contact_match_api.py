from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterList
import json
import re


def normalize_mobile(number):
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    return digits[-10:] if len(digits) >= 10 else None


@csrf_exempt
def match_contacts_with_users(request):

    if request.method != "POST":
        return JsonResponse(
            {"status": False, "message": "POST method required"},
            status=405
        )

    # -------- AUTH --------
    auth_header = request.headers.get("Authorization")
    user_id = None

    if auth_header and auth_header.startswith("Bearer "):
        token = AccessToken(auth_header.split(" ")[1])
        user_id = token.get("user_id")

    if not user_id:
        return JsonResponse(
            {"status": False, "message": "Unauthorized"},
            status=401
        )

    try:
        body = json.loads(request.body)
        phone_numbers = body.get("phone_numbers", [])

        if not isinstance(phone_numbers, list):
            return JsonResponse(
                {"status": False, "message": "phone_numbers must be a list"},
                status=400
            )

        # -------- Normalize numbers --------
        normalized_numbers = list(
            set(filter(None, map(normalize_mobile, phone_numbers)))
        )

        if not normalized_numbers:
            return JsonResponse({
                "status": True,
                "matched_count": 0,
                "data": []
            })

        # -------- DB MATCH + JOIN --------
        voters = (
            VoterList.objects
            .select_related("user")   # FK → VoterUserMaster
            .filter(mobile_no__in=normalized_numbers)
        )

        result = []
        for v in voters:
            user = v.user  # VoterUserMaster object

            result.append({
                "contact_mobile": v.mobile_no,
                "voter_list_id": v.voter_list_id,
                "voter_name": v.voter_name_eng,
                "assigned_user_id": user.user_id if user else None,
                "assigned_user_name": (
                    f"{user.first_name} {user.last_name}"
                    if user else None
                ),
                "assigned_user_mobile": user.mobile_no if user else None
            })

        return JsonResponse({
            "status": True,
            "requested_by_user_id": user_id,
            "uploaded_numbers": len(phone_numbers),
            "matched_count": len(result),
            "data": result
        })

    except Exception as e:
        return JsonResponse(
            {"status": False, "error": str(e)},
            status=500
        )
