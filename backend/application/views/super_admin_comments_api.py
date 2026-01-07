from ..models import ActivityLog
from .single_voters_api import format_indian_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from logger import logger
from ..models import VoterUserMaster


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def all_comments(request):
    logger.info("super_admin_comments_api: All comments request received")
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

    # -------- ROLE-BASED QUERY --------
    from django.db.models import Q

    privileged_roles = ["SuperAdmin"]

    if user.role.role_name in privileged_roles:   
        logs = (
            ActivityLog.objects
            .filter(new_data__has_key="comments")
            .select_related(
                "user",
                "voter",
                "voter__tag_id"   # for tag
            )
            .order_by("-created_at")
        )

        data = []
        for log in logs:
            voter = log.voter
            user = log.user

            data.append({
                # comment info
                "comment": log.new_data.get("comments"),
                "commented_at": format_indian_datetime(log.created_at),

                # user info
                "commented_by": (
                    f"{user.first_name} {user.last_name}".strip()
                    if user else None
                ),
                "commented_by_user_id": user.user_id if user else None,
                "commented_by_mobile": user.mobile_no if user else None,

                # voter info
                "voter_sr_no" : voter.sr_no if voter else None,
                "voter_list_id": voter.voter_list_id if voter else None,
                "voter_id": voter.voter_id if voter else None,
                "voter_name": voter.voter_name_eng if voter else None,
                "voter_tag": (
                    voter.tag_id.tag_name
                    if voter and voter.tag_id else None
                )
            })
        logger.info(f"super_admin_comments_api: Retrieved {len(data)} comments")
        return Response({
            "status": True,
            "count": len(data),
            "data": data
        })
    else:
        return Response(
            {"status": False, "message": "Not Authorized"},
            status=403
        )