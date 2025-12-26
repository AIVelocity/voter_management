from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterList,UserVoterContact, VoterUserMaster
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def print_voters_by_ids(request):
    pass

    if request.method != "POST":
        return Response(
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
        return Response(
            {"status": False, "message": "Unauthorized"},
            status=401
        )

    # ---------- READ BODY ----------
    try:
        body = request.data
    except json.JSONDecodeError:
        return Response(
            {"status": False, "message": "Invalid JSON"},
            status=400
        )

    voter_list_ids = body.get("voter_list_ids")

    if not isinstance(voter_list_ids, list) or not voter_list_ids:
        return Response(
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
        return Response(
            {"status": False, "message": "No voters found"},
            status=404
        )

    # ---------- FORMAT RESPONSE ----------
    voters = []
    for v in voters_qs:
        voters.append({
            "voter_list_id": v["voter_list_id"],
            "voter_name_mar": v["voter_name_marathi"],
            "yadivibhag": v["yadivibagh"],
            "anukramank": v["anukramank"],
            "voter_id": v["voter_id"],
            "voting_address": v["matdankendra"]
        })

    return Response({
        "status": True,
        "count": len(voters),
        "voters": voters
    })
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def matched_contacts_list(request):
    # user = request.user
    user_id = None
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = AccessToken(auth_header.split(" ")[1])
            user_id = token["user_id"]
        except Exception:
            pass
        
    if not user_id:
        return Response(
            {"status": False, "message": "Unauthorized"},
            status=401
        )
    

    # -------- GET USER & ROLE --------
    try:
        user = (
            VoterUserMaster.objects
            .select_related("role")
            .get(user_id=user_id)
        )
    except VoterUserMaster.DoesNotExist:
        return Response(
            {"status": False, "message": "User not found"},
            status=404
        )

    # -------- ROLE-BASED QUERY --------
    # if user.role.role_name in ["SuperAdmin", "Admin"]:
    #     qs = (
    #     UserVoterContact.objects
    #     .select_related("user", "voter")
    #     # .filter(user=user)
    #     .order_by("-created_at")
    # :
    qs = (
        UserVoterContact.objects
        .select_related("user", "voter")
        .filter(user=user)
        .order_by("-created_at")
    )
    data = []
    for obj in qs:
        data.append({
            "id": obj.id,
            "user_name": f"{obj.user.first_name} {obj.user.last_name}".strip(),
            "user_id": obj.user.user_id,
            "voter_id": obj.voter.voter_id,
            "voter_list_id": obj.voter.voter_list_id,
            "voter_name": obj.voter.voter_name_eng or obj.voter.voter_name_marathi,
            "contact_name": obj.contact_name,
            "mobile_no": obj.mobile_no,
            "created_at": obj.created_at,
        })
    return Response({
        "status": True,
        "message": ("Matched voter contacts fetched successfully"),
        "count": qs.count(),
        "data": data
    })
    # else:
        # return Response(
        #     {"status": False, "message": "Volunteer access not allowed"},
        #     status=403
        # )