from ..models import VoterList, VoterUserMaster
from django.db.models import Count
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from django.core.paginator import Paginator
from .search_api import apply_dynamic_initial_search
from .filter_api import apply_multi_filter,apply_tag_filter

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

def volunteer_voters_page_filter(request):
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))

    # -------- AUTH --------
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

    # -------- BASE QUERY (logged-in user only) --------
    qs = (
        VoterList.objects
        .select_related("tag_id")
        .filter(user_id=user_id)
        .order_by("voter_list_id")
    )
    
    search = request.GET.get("search")

    first_name = request.GET.get("first_name")
    middle_name = request.GET.get("middle_name")
    last_name = request.GET.get("last_name")

    age_max = request.GET.get("age_max")
    age_min = request.GET.get("age_min")

    location = request.GET.get("location")
    tag = request.GET.get("tag_id")
    gender = request.GET.get("gender")

    # STARTS WITH filters
    # first_starts = request.GET.get("first_starts")
    # middle_starts = request.GET.get("middle_starts")
    # last_starts = request.GET.get("last_starts")

    # ENDS WITH filters
    first_ends = request.GET.get("first_ends")
    middle_ends = request.GET.get("middle_ends")
    last_ends = request.GET.get("last_ends")
    
    kramank = request.GET.get("kramank")
    voter_id = request.GET.get("voter_id")
    
    religion = request.GET.get("religion")
    age_ranges = request.GET.get("age_ranges")
    # caste = request.GET.get("caste")

    # badge = request.GET.get("badge")
    
    # Apply advanced search (name + voter_id)
    if search:
        qs = apply_dynamic_initial_search(qs, search)

    # If Python converted to list → sort manually
    if isinstance(qs, list):
        qs.sort(key=lambda x: x.voter_list_id)

  
    if voter_id:
        qs = qs.filter(voter_id__icontains=voter_id)
    
    if kramank:
        qs = qs.filter(kramank__icontains=kramank)
        
    # Field filters
    if first_name:
        # qs = qs.filter(first_name__icontains=first_name)
        qs = qs.filter(first_name__istartswith=first_name)
        

    if middle_name:
        # qs = qs.filter(middle_name__icontains=middle_name)
        qs = qs.filter(middle_name__istartswith=middle_name)
        

    if last_name:
        # qs = qs.filter(last_name__icontains=last_name)
        qs = qs.filter(last_name__istartswith=last_name)


    from django.db.models import Q

    if age_ranges:
        age_q = Q()
        ranges = age_ranges.split(",")

        for r in ranges:
            try:
                min_age, max_age = r.split("-")
                age_q |= Q(
                    age_eng__gte=int(min_age.strip()),
                    age_eng__lte=int(max_age.strip())
                )
            except ValueError:
                continue  # skip invalid ranges

        qs = qs.filter(age_q)

    # if age_max:
    #     qs = qs.filter(age_eng__lte=age_max)

    # if age_min:
    #     qs = qs.filter(age_eng__gte=age_min)

    if location:
        qs = qs.filter(location__icontains=location)
     
    
    # if sort:
    #     qs = qs.order_by(sort)
    # else:
    #     qs = qs.order_by(voter)

    # if gender:
    #     qs = qs.filter(gender_eng__iexact=gender)

    # Apply ENDS WITH filters
    if first_ends:
        qs = qs.filter(first_name__iendswith=first_ends)
    
    if middle_ends:
        qs = qs.filter(middle_name__iendswith=middle_ends)
    
    if last_ends:
        qs = qs.filter(last_name__iendswith=last_ends)
        
    qs = apply_multi_filter(qs, "cast", request.GET.get("caste"))
    qs = apply_multi_filter(qs, "religion_id", request.GET.get("religion"))
    qs = apply_multi_filter(qs, "occupation", request.GET.get("occupation"))
    qs = apply_multi_filter(qs, "gender_eng", request.GET.get("gender"))
    qs = apply_tag_filter(qs, request.GET.get("tag_id"))
    
    # Pagination
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = []
    for v in page_obj:
        data.append({
            "sr_no" : v.serial_number,
            "voter_list_id": v.voter_list_id,
            "voter_name_eng": v.voter_name_eng,
            "voter_id": v.voter_id,
            "gender": v.gender_eng,
            "location": v.location,
            "badge": v.badge,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "kramank": v.kramank,
            "age":v.age_eng,
            "ward_id": v.ward_no
        })

    return JsonResponse({
        "status": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })