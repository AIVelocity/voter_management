from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterList
import json


@csrf_exempt
def print_voters_by_ids(request):
    pass

    if request.method != "POST":
        return JsonResponse(
            {"status": False, "message": "POST method required"},
            status=405
        )

    # ---------- AUTH ----------
    user_id = None
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = AccessToken(auth_header.split(" ")[1])
            user_id = token["user_id"]
        except Exception:
            pass

    if not user_id:
        return JsonResponse(
            {"status": False, "message": "Unauthorized"},
            status=401
        )

    # ---------- READ BODY ----------
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": False, "message": "Invalid JSON"},
            status=400
        )

    voter_list_ids = body.get("voter_list_ids")

    if not isinstance(voter_list_ids, list) or not voter_list_ids:
        return JsonResponse(
            {"status": False, "message": "voter_list_ids must be a non-empty list"},
            status=400
        )

    # ---------- FETCH DATA (MAPPED TO PRINT TABLE) ----------
    voters_qs = (
        VoterList.objects
        .filter(voter_list_id__in=voter_list_ids)
        .values(
            "voter_list_id",
            "voter_id",
            
            "voter_name_marathi",
            "yadivibagh",
            "anukramank",
            "matdankendra",
        )
    )


    if not voters_qs.exists():
        return JsonResponse(
            {"status": False, "message": "No voters found"},
            status=404
        )

    # ---------- FORMAT RESPONSE ----------
    voters = []
    for v in voters_qs:
        voters.append({
            "voter_list_id": v["voter_list_id"],
            "voter_name_mar": v["print_details__voter_name_marathi"],
            "yadivibhag": v["print_details__yadivibhag"],
            "anukramank": v["print_details__anukramank"],
            "voter_id": v["print_details__voterid"],
            "voting_address": v["print_details__voting_center_address"]
        })

    return JsonResponse({
        "status": True,
        "count": len(voters),
        "voters": voters
    })
