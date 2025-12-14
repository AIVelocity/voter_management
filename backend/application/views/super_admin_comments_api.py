from django.http import JsonResponse
from ..models import ActivityLog
from .single_voters_api import format_indian_datetime   # adjust import if needed


def all_comments(request):

    logs = (
        ActivityLog.objects
        .filter(new_data__has_key="comments")
        .select_related("user", "voter")
        .order_by("-created_at")
    )

    data = []
    for log in logs:
        data.append({
            "comment": log.new_data.get("comments"),
            "commented_at": format_indian_datetime(log.created_at), 
            "commented_by": (
                f"{log.user.first_name} {log.user.last_name}"
                if log.user else None
            ),
            "commented_by_user_id": log.user.user_id if log.user else None,
            "voter_list_id": log.voter.voter_list_id if log.voter else None
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })
