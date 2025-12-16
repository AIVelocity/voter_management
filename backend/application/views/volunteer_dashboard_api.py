from ..models import VoterList, VoterUserMaster
from django.db.models import Count
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from django.core.paginator import Paginator

def volunteer_dashboard(request):

    # ---------------- AUTH ----------------
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

    # Optional: fetch user details
    user = (
        VoterUserMaster.objects
        .filter(user_id=user_id)
        .values("user_id", "first_name", "last_name", "mobile_no", "role__role_name")
        .first()
    )

    # ---------------- BASIC COUNTS ----------------

    assigned_count = VoterList.objects.filter(user_id=user_id).count()

    visited_count = VoterList.objects.filter(
        user_id=user_id,
        check_progress_date__isnull=False
    ).count()

    pending_count = assigned_count - visited_count

    # ---------------- WEEK CALC ----------------

    today = timezone.now().date()

    start_of_week = today - timedelta(days=(today.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)

    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)

    this_week_count = VoterList.objects.filter(
        user_id=user_id,
        check_progress_date__range=(start_of_week, end_of_week)
    ).count()

    last_week_count = VoterList.objects.filter(
        user_id=user_id,
        check_progress_date__range=(start_of_last_week, end_of_last_week)
    ).count()

    week_difference = this_week_count - last_week_count

    # ---------------- DAYWISE ----------------

    daily_qs = (
        VoterList.objects
        .filter(
            user_id=user_id,
            check_progress_date__range=(start_of_week, end_of_week)
        )
        .values("check_progress_date")
        .annotate(daily_count=Count("voter_list_id"))
    )

    daily_map = defaultdict(int)
    for row in daily_qs:
        daily_map[row["check_progress_date"]] = row["daily_count"]

    daywise = []
    running_total = 0

    for i in range(7):
        d = start_of_week + timedelta(days=i)
        running_total += daily_map[d]

        daywise.append({
            "date": d,
            "day": d.strftime("%A"),
            "daily_count": daily_map[d],
            "cumulative_count": running_total
        })

    # ---------------- TAG COUNTS (VOLUNTEER ONLY) ----------------

    golden_color_tags = VoterList.objects.filter(user_id=user_id, tag_id=4).count()
    green_color_tags = VoterList.objects.filter(user_id=user_id, tag_id=1).count()
    orange_color_tags = VoterList.objects.filter(user_id=user_id, tag_id=2).count()
    red_color_tags = VoterList.objects.filter(user_id=user_id, tag_id=3).count()

    # ---------------- RESPONSE ----------------

    return JsonResponse({
        "SUCCESS": True,
        "data": {
            "user": user,
            "assigned": assigned_count,
            "visited": visited_count,
            "pending": pending_count,

            "this_week": this_week_count,
            "last_week": last_week_count,
            "week_difference": week_difference,

            "daywise_check_progress": daywise,
            "golden_voter": golden_color_tags,
            "guaranteed_voter": green_color_tags,
            "unsure_voter": orange_color_tags,
            "red": red_color_tags
        }
    })


def volunteer_voters_page(request):
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))

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
        

    qs = (
        VoterList.objects
        .select_related("tag_id")
        .filter(user_id=user_id)
        .order_by("ward_no", "voter_list_id")
    )
    
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = []

    for v in page_obj:
        data.append({
            "sr_no" : v.serial_number,
            "voter_list_id": v.voter_list_id,
            "voter_id": v.voter_id,
            "first_name":v.first_name,
            "last_name" : v.last_name,
            "voter_name_marathi": v.voter_name_marathi,
            "voter_name_eng": v.voter_name_eng,
            "kramank": v.kramank,
            "age": v.age_eng,
            "gender": v.gender_eng,
            "ward_id": v.ward_no,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "badge": v.badge,
            "location": v.location
        })

    return JsonResponse({
        "SUCCESS": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })