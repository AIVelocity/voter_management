from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterList,UserVoterContact, VoterUserMaster
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.core.paginator import Paginator
from logger import logger
from .view_utils import log_action_user

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def print_voters_by_ids(request):
    logger.info("print_api: Print voters by IDs request received")
    user = request.user
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
            "kramank",
            "age_eng",
            "gender_eng",
            "yadivibagh",
            "anukramank",
            "matdankendra"
        )
    )


    if not voters_qs.exists():
        log_action_user(
    request=request,
    user=user,
    action="PRINT_VOTERS_BY_IDS_NOT_FOUND",
    module="PRINT",
    status="FAILED",
    metadata={
        "requested_ids_count": len(voter_list_ids)
    }
)

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
            "voting_address": v["matdankendra"],
            "kramank": v["kramank"],
            "age_eng": v["age_eng"],
            "gender_eng": v["gender_eng"]
        })
    logger.info(f"print_api: Retrieved {len(voters)} voters for printing")
    log_action_user(
        request=request,
        user=user,
        action="PRINT_VOTERS_BY_IDS",
        module="PRINT",
        metadata={
            "requested_ids_count": len(voter_list_ids),
            "returned_count": len(voters)
        }
    )

    return Response({
        "status": True,
        "count": len(voters),
        "voters": voters
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_voters_for_print(request):
    logger.info("print_api: List voters for print request received")
    # ---------- AUTH ----------
    user = request.user

    # ---------- PAGINATION ----------
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))

    # ---------- ROLE BASED QUERY ----------
    privileged_roles = ["Volunteer"]

    if user.role.role_name in privileged_roles:
        has_assigned_voters = VoterList.objects.filter(user_id=user.user_id).exists()

        if has_assigned_voters:
            qs = (
                VoterList.objects
                .filter(user_id=user.user_id)
                .order_by("sr_no")
            )
        else:
            qs = (
                VoterList.objects
                .order_by("sr_no")
            )
    else:
        qs = (
            VoterList.objects
            .order_by("sr_no")
        )

    # ---------- SELECT ONLY REQUIRED FIELDS ----------
    qs = qs.values(
        "voter_list_id",
        "voter_id",
        "voter_name_marathi",
        "kramank",
        "age_eng",
        "gender_eng",
        "yadivibagh",
        "anukramank",
        "matdankendra",
    )

    # ---------- PAGINATE ----------
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    # ---------- FORMAT RESPONSE ----------
    voters = []
    for v in page_obj:
        voters.append({
            "voter_list_id": v["voter_list_id"],
            "voter_name_mar": v["voter_name_marathi"],
            "yadivibhag": v["yadivibagh"],
            "anukramank": v["anukramank"],
            "voter_id": v["voter_id"],
            "voting_address": v["matdankendra"],
            "kramank": v["kramank"],
            "age_eng": v["age_eng"],
            "gender_eng": v["gender_eng"]
        })
    logger.info(f"print_api: Retrieved page {page} with {len(voters)} voters for printing")
    log_action_user(
        request=request,
        user=user,
        action="LIST_VOTERS_FOR_PRINT",
        module="PRINT",
        metadata={
            "page": page,
            "page_size": size,
            "records_returned": len(voters),
            "total_records": paginator.count
        }
    )

    return Response({
        "status": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(voters),
        "voters": voters
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def matched_contacts_list(request):
    logger.info("print_api: Matched contacts list request received")
    user = request.user
    user_id = user.user_id 

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
    logger.info(f"print_api: Retrieved {len(data)} matched contacts for user {user.user_id}")
    return Response({
        "status": True,
        "message": ("Matched voter contacts fetched successfully"),
        "count": qs.count(),
        "data": data
    })
