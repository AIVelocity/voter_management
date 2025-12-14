from ..models import VoterList,VoterRelationshipDetails,VoterUserMaster
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
from django.core.paginator import Paginator, EmptyPage
from collections import defaultdict


# main dashboard api
def dashboard(request):

    # today = timezone.now().date()
    # start_of_week = today - timedelta(days=today.weekday())
    # start_of_last_week = start_of_week - timedelta(days=7)
    # end_of_last_week = start_of_week - timedelta(days=1)

    # # This week
    # this_week_count = VoterList.objects.filter(
    #     check_progress=True,
    #     check_progress_date__gte=start_of_week
    # ).count()

    # # Last week
    # last_week_count = VoterList.objects.filter(
    #     check_progress=True,
    #     check_progress_date__range=(start_of_last_week, end_of_last_week)
    # ).count()

    # difference = this_week_count - last_week_count
    today = timezone.now().date()

    # Sunday start
    start_of_week = today - timedelta(days=(today.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)

    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)

    this_week_count = VoterList.objects.filter(
        # check_progress=True,
        check_progress_date__range=(start_of_week, end_of_week)
    ).count()

    last_week_count = VoterList.objects.filter(
        # check_progress=True,
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

    karyakarta_users = (
        VoterUserMaster.objects
        .filter(role__role_name="Volunteer")
        .annotate(
            voter_allocated_count=Count("voterlist"),
            # karyakarta_allocated_count=Coalesce(
            # Subquery(created_karyakarta_count, output_field=IntegerField()),
            # Value(0),)
        )
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no",
            "voter_allocated_count",
            # "karyakarta_allocated_count"
        )
    )

    # daywise = (
    #     VoterList.objects
    #     .filter(check_progress=True, user__role__role_name="Admin")   # only checked voters under admin
    #     .values("check_progress_date")                     # group by admin + date
    #     .annotate(count=Count("voter_list_id"))                       # count checked voters
    #     .order_by("check_progress_date")
    # )
    
    today = timezone.now().date()
    start_of_week = today - timedelta(days=(today.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)

    daily_qs = (
        VoterList.objects
        .filter(
            # check_progress=True,
            check_progress_date__range=(start_of_week, end_of_week),
            # user__role__role_name="Admin"
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

    total_visited = VoterList.objects.filter(check_progress_date__isnull=False).count()
    
    return JsonResponse({
        "SUCCESS": True,
        "data" : { 
                "golden_voter":golden_color_tags,
                "guaranteed_voter" :green_color_tags,
                "unsure_voter" : orange_color_tags,
                "red_color_tags" : red_color_tags,
                "total_voters": total_voters,
                "admins": list(admin_users),  # convert queryset to list
                "karyakartas": list(karyakarta_users),
                "daywise_check_progress": list(daywise),
                "total_visited" : total_visited,
                "week_difference": difference,
                "this_week": this_week_count,
                "last_week": last_week_count 
        }
    })

def admin_allocation_panel(request):

    total_voters = VoterList.objects.count()

    admins = (
        VoterUserMaster.objects
        .filter(role__role_name="Admin")
        .annotate(
            assigned_count=Count("voterlist")
        )
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no",
            "assigned_count"
        )
    )

    karyakarta_qs = (
        VoterUserMaster.objects
        .filter(role__role_name="Volunteer")
        .annotate(
            voter_allocated_count=Count("voterlist")
        )
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no",
            "voter_allocated_count"
        )
    )

    total_karyakartas = karyakarta_qs.count()
    assigned_karyakartas = len([k for k in karyakarta_qs if k["voter_allocated_count"] > 0])
    unassigned_karyakartas = total_karyakartas - assigned_karyakartas

    total_admins = admins.count()
    assigned_admins = len([a for a in admins if a["assigned_count"] > 0])
    unassigned_admins = total_admins - assigned_admins

    admin_list = [
        {
            "user_id": a["user_id"],
            "name": f"{a['first_name']} {a['last_name']}",
            "mobile": a["mobile_no"],
            "assigned_count": a["assigned_count"],
            "status": "assigned" if a["assigned_count"] > 0 else "unassigned"
        }
        for a in admins
    ]

    karyakarta_list = [
        {
            "user_id": k["user_id"],
            "name": f"{k['first_name']} {k['last_name']}",
            "mobile": k["mobile_no"],
            "assigned_count": k["voter_allocated_count"],
            "status": "assigned" if k["voter_allocated_count"] > 0 else "unassigned"
        }
        for k in karyakarta_qs
    ]
    
    # ---------------- SECOND SCREEN FILTERS ----------------

    assigned_admin_list = [
        a for a in admin_list if a["assigned_count"] > 0
    ]

    assigned_karyakarta_list = [
        k for k in karyakarta_list if k["assigned_count"] > 0
    ]

    # ---------------- THIRD SCREEN (UNASSIGNED) ----------------

    unassigned_admin_list = [
        a for a in admin_list if a["assigned_count"] == 0
    ]

    unassigned_karyakarta_list = [
        k for k in karyakarta_list if k["assigned_count"] == 0
    ]

    return JsonResponse({
        "SUCCESS" :True,
        "data":{ 
            "summary": {
                "total_admins": total_admins,
                "assigned_admins": assigned_admins,
                "unassigned_admins": unassigned_admins,
                "total_voters": total_voters,
                "total_karyakartas": total_karyakartas,
                "assigned_karyakartas": assigned_karyakartas,
                "unassigned_karyakartas": unassigned_karyakartas
                },
                
                # ---------- FIRST SCREEN ----------
                "allocated_first_screen_admin": admin_list,
                "allocated_first_screen_karyakartas": karyakarta_list,

                # ---------- SECOND SCREEN ----------
                "allocated_second_screen_admin": assigned_admin_list,
                "allocated_second_screen_karyakartas": assigned_karyakarta_list,
                
                # ---------- THIRD SCREEN (UNASSIGNED) ---------
                "allocated_third_screen_admin": unassigned_admin_list,
                "allocated_third_screen_karyakartas": unassigned_karyakarta_list
            }
        }
    )


def unassigned_voters(request):

    # -------- GET PARAMS --------
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 100)) 

    # -------- BASE QUERY --------
    queryset = (
        VoterList.objects
        .filter(user__isnull=True)
        .values(
            "voter_list_id",
            "sr_no",
            "voter_id",
            "voter_name_eng",
            "voter_name_marathi",
            "mobile_no",
            "ward_no",
            "age",
            "gender_eng",
            "badge",
            "location"
        )
        .order_by("voter_list_id")
    )

    total_count = queryset.count()

    # -------- PAGINATION --------
    paginator = Paginator(queryset, page_size)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({
            "status": True,
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "voters": []
        })

    return JsonResponse({
        "status": True,
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "voters": list(page_obj.object_list)
    })


@csrf_exempt
def assign_voters_to_karyakarta(request):

    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        body = json.loads(request.body)

        karyakarta_user_id = body.get("karyakarta_user_id")
        voter_ids = body.get("voter_ids", [])

        if not karyakarta_user_id or not voter_ids:
            return JsonResponse({
                "status": False,
                "message": "karyakarta_user_id and voter_ids are required"
            }, status=400)

        # Validate karyakarta
        try:
            karyakarta = VoterUserMaster.objects.get(
                user_id=karyakarta_user_id
            )
        except VoterUserMaster.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Karyakarta not found"
            }, status=404)

        with transaction.atomic():
            updated_count = (
                VoterList.objects
                .filter(
                    voter_list_id__in=voter_ids,
                    user__isnull=True  
                )
                .update(user=karyakarta)
            )

        return JsonResponse({
            "status": True,
            "assigned_count": updated_count,
            "message": "Voters assigned successfully"
        })

    except Exception as e:
        return JsonResponse({
            "status": False,
            "error": str(e)
        }, status=500)


def auto_select_unassigned_voters(request):

    try:
        count = int(request.GET.get("count", 0))
    except ValueError:
        return JsonResponse({
            "status": False,
            "message": "Invalid count"
        }, status=400)

    if count <= 0:
        return JsonResponse({
            "status": False,
            "message": "Count must be greater than 0"
        }, status=400)

    voters = (
        VoterList.objects
        .filter(user__isnull=True)
        .order_by("sr_no")
        .values(
            "voter_list_id",
            "sr_no",
            "voter_id",
            "voter_name_eng",
            "voter_name_marathi",
            "mobile_no",
            "ward_no",
            "age",
            "gender_eng",
            "badge",
            "location"
        )[:count]
    )

    return JsonResponse({
        "status": True,
        "requested_count": count,
        "returned_count": len(voters),
        "voters": list(voters),
        "voter_ids": [v["voter_list_id"] for v in voters]
    })


# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.db import transaction
# from ..models import VoterList, VoterUserMaster
# import json


# @csrf_exempt
# def auto_assign_unassigned_voters(request):

#     if request.method != "POST":
#         return JsonResponse({
#             "status": False,
#             "message": "POST method required"
#         }, status=405)

#     try:
#         body = json.loads(request.body)

#         karyakarta_user_id = body.get("karyakarta_user_id")
#         count = body.get("count")

#         if not karyakarta_user_id or not count:
#             return JsonResponse({
#                 "status": False,
#                 "message": "karyakarta_user_id and count are required"
#             }, status=400)

#         count = int(count)
#         if count <= 0:
#             return JsonResponse({
#                 "status": False,
#                 "message": "Count must be greater than 0"
#             }, status=400)

#         #  validate karyakarta
#         try:
#             karyakarta = VoterUserMaster.objects.get(user_id=karyakarta_user_id)
#         except VoterUserMaster.DoesNotExist:
#             return JsonResponse({
#                 "status": False,
#                 "message": "Karyakarta not found"
#             }, status=404)

#         with transaction.atomic():

#             # fetch first N unassigned voters
#             voters = list(
#                 VoterList.objects
#                 .select_for_update()               # prevents race condition
#                 .filter(user__isnull=True)
#                 .order_by("sr_no")
#                 .values_list("voter_list_id", flat=True)[:count]
#             )

#             if not voters:
#                 return JsonResponse({
#                     "status": True,
#                     "assigned_count": 0,
#                     "message": "No unassigned voters available"
#                 })

#             # assign them
#             updated = (
#                 VoterList.objects
#                 .filter(voter_list_id__in=voters, user__isnull=True)
#                 .update(user=karyakarta)
#             )

#         return JsonResponse({
#             "status": True,
#             "assigned_count": updated,
#             "assigned_voter_ids": voters
#         })

#     except Exception as e:
#         return JsonResponse({
#             "status": False,
#             "error": str(e)
#         }, status=500)
