from django.http import JsonResponse
from ..models import ActivityLog
from .single_voters_api import format_indian_datetime


def all_comments(request):

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
            "voter_sr_no" : voter.serial_number if voter else None,
            "voter_list_id": voter.voter_list_id if voter else None,
            "voter_id": voter.voter_id if voter else None,
            "voter_name": voter.voter_name_eng if voter else None,
            "voter_tag": (
                voter.tag_id.tag_name
                if voter and voter.tag_id else None
            )
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })
