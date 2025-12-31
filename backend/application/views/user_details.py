from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator, EmptyPage
from ..models import VoterUserMaster
from .single_voters_api import format_indian_datetime, make_aware_if_needed 
from logger import logger

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_all_users(request):
    logger.info("super_admin_dashboard_api: List all users request received")
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 50))
    role = request.GET.get("role")   # optional filter

    qs = (
        VoterUserMaster.objects
        .select_related("role")
        .order_by("-created_date")
    )

    if role:
        qs = qs.filter(role__role_name__iexact=role)

    paginator = Paginator(qs, size)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return Response({
            "status": True,
            "data": [],
            "page": page,
            "total_pages": paginator.num_pages,
            "total_records": paginator.count
        })

    data = []

    for user in page_obj:
        data.append({
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "mobile_no": user.mobile_no,
            "role": user.role.role_name if user.role else None,
            # "is_active": user.is_active,
            # "is_staff": user.is_staff,
            "created_at": format_indian_datetime(
        make_aware_if_needed(user.created_date))
        })
    logger.info(f"super_admin_dashboard_api: Retrieved page {page} with {len(data)} users")
    return Response({
        "status": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })
