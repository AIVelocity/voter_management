from ..models import VoterList,VoterRelationshipDetails,VoterUserMaster
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta


def dashboard(request):


    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)

    # This week
    this_week_count = VoterList.objects.filter(
        check_progress=True,
        check_progress_date__gte=start_of_week
    ).count()

    # Last week
    last_week_count = VoterList.objects.filter(
        check_progress=True,
        check_progress_date__range=(start_of_last_week, end_of_last_week)
    ).count()

    difference = this_week_count - last_week_count
    
    total_voters = VoterList.objects.count()
    # voter_list_count = VoterList.objects.filter(vo)
    golden_color_tags = VoterList.objects.filter(tag_id = 4).count()
    red_color_tags = VoterList.objects.filter(tag_id = 3).count()
    orange_color_tags = VoterList.objects.filter(tag_id = 2).count()
    green_color_tags = VoterList.objects.filter(tag_id = 1).count()

    # Fetch all users whose role is Admin AND count how many voters are assigned to them
    admin_users = (
        VoterUserMaster.objects
        .filter(role__role_name="Admin")
        .annotate(voter_allocated_count=Count("voterlist"))
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no",
            "voter_allocated_count"
        )
    )
    daywise = (
        VoterList.objects
        .filter(check_progress=True, user__role__role_name="Admin")   # only checked voters under admin
        .values("check_progress_date")                     # group by admin + date
        .annotate(count=Count("voter_list_id"))                       # count checked voters
        .order_by("check_progress_date")
    )
    
    total_visited = VoterList.objects.filter(check_progress=True).count()
    
    return JsonResponse({
        "golden_color_tags":golden_color_tags,
        "green_color_tags" :green_color_tags,
        "orange_color_tags" : orange_color_tags,
        "red_color_tags" : red_color_tags,
        "total_voters": total_voters,
        "admins": list(admin_users),  # convert queryset to list
        "daywise_check_progress": list(daywise),
        "total_visited" : total_visited,
        "week_difference": difference,
        "this_week": this_week_count,
        "last_week": last_week_count
    })
