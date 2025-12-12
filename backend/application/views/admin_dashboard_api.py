from ..models import VoterList,VoterRelationshipDetails,VoterUserMaster
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce


# main dashboard api
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

    created_karyakarta_count = (
        VoterUserMaster.objects
        .filter(created_by=OuterRef('user_id'))
        .values('created_by')
        .annotate(count=Count('*'))
        .values('count')
    )

    # Fetch all users whose role is Admin AND count how many voters are assigned to them
    admin_users = (
        VoterUserMaster.objects
        .filter(role__role_name="Admin")
        .annotate(
            voter_allocated_count=Count("voterlist"),
            karyakarta_allocated_count=Coalesce(
            Subquery(created_karyakarta_count, output_field=IntegerField()),
            Value(0),)
        )
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no",
            "voter_allocated_count",
            "karyakarta_allocated_count"
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

def admin_allocation_panel(request):

    total_voters = VoterList.objects.count()

    admins = (
        VoterUserMaster.objects
        .filter(role__role_name="Admin")
        .annotate(
            assigned_count=Count("voterlist")
            # range_start=Min("voterlist__sr_no"),
            # range_end=Max("voterlist__sr_no"),
        )
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no",
            "assigned_count",
            # "range_start",
            # "range_end"
        )
    )

    # summary
    total_admins = admins.count()
    assigned_admins = len([a for a in admins if a["assigned_count"] > 0])
    unassigned_admins = total_admins - assigned_admins

    # convert to frontend format
    admin_list = []

    for a in admins:
        admin_list.append({
            "user_id": a["user_id"],
            "name": f"{a['first_name']} {a['last_name']}",
            "mobile": a["mobile_no"],
            "assigned_count": a["assigned_count"],
            # "range_start": a["range_start"],
            # "range_end": a["range_end"],
            "status": "assigned" if a["assigned_count"] > 0 else "unassigned"
        })
        
    # second_screen_assigned_admins = (
    #     VoterUserMaster.objects.filter(role__role_name = "Admin")
    #     .annotate(
    #         assigned_count=Count("voterlist")
    #     )
    #     .filter(assigned_count__gt=0)
    #     .values(
    #         "user_id",
    #         "first_name",
    #         "last_name",
    #         "mobile_no",
    #         "assigned_count"
    #     )
    #     .order_by("first_name")
    # )
        

    return JsonResponse({
        "summary": {
            "total_admins": total_admins,
            "assigned_admins": assigned_admins,
            "unassigned_admins": unassigned_admins,
            "total_voters": total_voters
        },
        "allocated_first_screen": admin_list,
        # "allocated_second_screen":second_screen_assigned_admins
    })
