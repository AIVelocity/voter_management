from .voters_info_api import split_marathi_name
from ..models import VoterList,VoterUserMaster
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce
from django.db import transaction
from django.core.paginator import Paginator
from collections import defaultdict
from .filter_api import apply_multi_filter,apply_tag_filter
from .search_api import apply_dynamic_initial_search
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):

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

    # total_visited = VoterList.objects.filter(check_progress_date__isnull=False).count()
    total_visited = red_color_tags + orange_color_tags + green_color_tags + golden_color_tags
    
    return Response({
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

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
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
    
    members = []

    # ---------- ADMINS ----------
    for a in admins:
        members.append({
            "user_id": a["user_id"],
            "name": f"{a['first_name']} {a['last_name']}",
            "mobile": a["mobile_no"],
            "assigned_count": a["assigned_count"],
            "role": "Admin",
            "status": "assigned" if a["assigned_count"] > 0 else "unassigned"
        })

    # ---------- KARYAKARTAS ----------
    for k in karyakarta_qs:
        members.append({
            "user_id": k["user_id"],
            "name": f"{k['first_name']} {k['last_name']}",
            "mobile": k["mobile_no"],
            "assigned_count": k["voter_allocated_count"],
            "role": "Karyakarta",
            "status": "assigned" if k["voter_allocated_count"] > 0 else "unassigned"
        })

    allocated_first_screen = members

    # ---------- SECOND SCREEN (ASSIGNED) ----------
    allocated_second_screen = [
        m for m in members if m["assigned_count"] > 0
    ]

    # ---------- THIRD SCREEN (UNASSIGNED) ----------
    allocated_third_screen = [
        m for m in members if m["assigned_count"] == 0
    ]

    total_admins_karyakarta = total_admins + total_karyakartas
    total_assigned_admins_karyakarta = assigned_admins + assigned_karyakartas
    total_unassigned_admins_karyakarta = unassigned_admins + unassigned_karyakartas
    return Response({
        "SUCCESS" :True,
        "data":{ 
            "summary": {
                "total_admins": total_admins,
                "assigned_admins": assigned_admins,
                "unassigned_admins": unassigned_admins,
                "total_voters": total_voters,
                "total_karyakartas": total_admins_karyakarta ,
                "assigned_karyakartas": total_assigned_admins_karyakarta,
                "unassigned_karyakartas": total_unassigned_admins_karyakarta
                },
                
                # # ---------- FIRST SCREEN ----------
                # "allocated_first_screen_admin": admin_list,
                # "allocated_first_screen_karyakartas": karyakarta_list,

                # # ---------- SECOND SCREEN ----------
                # "allocated_second_screen_admin": assigned_admin_list,
                # "allocated_second_screen_karyakartas": assigned_karyakarta_list,
                
                # # ---------- THIRD SCREEN (UNASSIGNED) ---------
                # "allocated_third_screen_admin": unassigned_admin_list,
                # "allocated_third_screen_karyakartas": unassigned_karyakarta_list
             # ---------- ALL MEMBERS ----------
                "allocated_members": allocated_first_screen,

                # ---------- ASSIGNED ----------
                "allocated_assigned_members": allocated_second_screen,

                # ---------- UNASSIGNED ----------
                "allocated_unassigned_members": allocated_third_screen
    }
        }
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unassigned_voters(request):
    lang = request.headers.get("Accept-Language", "en")
    is_marathi = lang.lower().startswith("mr")
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))
    search = request.GET.get("search")

    first_name = request.GET.get("first_name")
    middle_name = request.GET.get("middle_name")
    last_name = request.GET.get("last_name")

    age_max = request.GET.get("age_max")
    age_min = request.GET.get("age_min")

    location = request.GET.get("location")
    tag = request.GET.get("tag_id")
    gender = request.GET.get("gender")

    first_ends = request.GET.get("first_ends")
    middle_ends = request.GET.get("middle_ends")
    last_ends = request.GET.get("last_ends")
    
    kramank = request.GET.get("kramank")
    voter_id = request.GET.get("voter_id")
    
    religion = request.GET.get("religion")
    age_ranges = request.GET.get("age_ranges")
    # caste = request.GET.get("caste")

    # badge = request.GET.get("badge")

    qs = VoterList.objects.select_related("tag_id").filter(user__isnull=True).order_by("sr_no")
    
    # Apply advanced search (name + voter_id)
    if search:
        qs = apply_dynamic_initial_search(qs, search)

    
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

    if location:
        qs = qs.filter(location__icontains=location)
    
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
        if is_marathi:
            first_name, middle_name, last_name = split_marathi_name(
                v.voter_name_marathi
            )

            voter_name_eng = v.voter_name_marathi
            age_eng = v.age
            gender_eng = v.gender
        else:
            first_name = v.first_name
            middle_name = v.middle_name
            last_name = v.last_name

            voter_name_eng = v.voter_name_eng
            age_eng = v.age_eng
            gender_eng = v.gender_eng
            
        data.append({
            "sr_no" : v.sr_no,
            "voter_list_id": v.voter_list_id,
            "voter_name_eng": voter_name_eng,
            "voter_id": v.voter_id,
            "gender": gender_eng,
            "location": v.location,
            "badge": v.badge,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "kramank": v.kramank,
            "age":age_eng,
            "ward_id": v.ward_no
        })

    return Response({
        "status": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_voters_to_karyakarta(request):

    if request.method != "POST":
        return Response({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        body = request.data

        karyakarta_user_id = body.get("karyakarta_user_id")
        voter_ids = body.get("voter_ids", [])

        if not karyakarta_user_id or not voter_ids:
            return Response({
                "status": False,
                "message": "karyakarta_user_id and voter_ids are required"
            }, status=400)

        # Validate karyakarta
        try:
            karyakarta = VoterUserMaster.objects.get(
                user_id=karyakarta_user_id
            )
        except VoterUserMaster.DoesNotExist:
            return Response({
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

        return Response({
            "status": True,
            "assigned_count": updated_count,
            "message": "Voters assigned successfully"
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auto_select_unassigned_voters(request):

    if request.method != "POST":
        return Response({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        body = request.data

        karyakarta_user_id = body.get("karyakarta_user_id")
        count = body.get("count")

        if not karyakarta_user_id or not count:
            return Response({
                "status": False,
                "message": "karyakarta_user_id and count are required"
            }, status=400)

        count = int(count)
        if count <= 0:
            return Response({
                "status": False,
                "message": "Count must be greater than 0"
            }, status=400)

        #  validate karyakarta
        try:
            karyakarta = VoterUserMaster.objects.get(user_id=karyakarta_user_id)
        except VoterUserMaster.DoesNotExist:
            return Response({
                "status": False,
                "message": "Karyakarta not found"
            }, status=404)

        with transaction.atomic():

            # fetch first N unassigned voters
            voters = list(
                VoterList.objects
                .select_for_update()               # prevents race condition
                .filter(user__isnull=True)
                .order_by("sr_no")
                .values_list("voter_list_id", flat=True)[:count]
            )

            if not voters:
                return Response({
                    "status": True,
                    "assigned_count": 0,
                    "message": "No unassigned voters available"
                })

            # assign them
            updated = (
                VoterList.objects
                .filter(voter_list_id__in=voters, user__isnull=True)
                .update(user=karyakarta)
            )

        return Response({
            "status": True,
            "assigned_count": updated,
            "assigned_voter_ids": voters,
            "message" : "Voters Assigned successfully"
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auto_unassign_voters(request):

    if request.method != "POST":
        return Response({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        body = request.data

        karyakarta_user_id = body.get("karyakarta_user_id")
        count = body.get("count")

        if not karyakarta_user_id or not count:
            return Response({
                "status": False,
                "message": "karyakarta_user_id and count are required"
            }, status=400)

        count = int(count)
        if count <= 0:
            return Response({
                "status": False,
                "message": "Count must be greater than 0"
            }, status=400)

        # Validate karyakarta
        try:
            karyakarta = VoterUserMaster.objects.get(user_id=karyakarta_user_id)
        except VoterUserMaster.DoesNotExist:
            return Response({
                "status": False,
                "message": "Karyakarta not found"
            }, status=404)

        with transaction.atomic():

            # fetch last N assigned voters for this karyakarta
            voters = list(
                VoterList.objects
                .select_for_update()               # prevents race condition
                .filter(user=karyakarta)
                .order_by("-sr_no")
                .values_list("voter_list_id", flat=True)[:count]
            )

            if not voters:
                return Response({
                    "status": True,
                    "unassigned_count": 0,
                    "message": "No assigned voters available for this karyakarta"
                })

            # unassign them
            updated = (
                VoterList.objects
                .filter(voter_list_id__in=voters, user=karyakarta)
                .update(user=None)
            )

        return Response({
            "status": True,
            "unassigned_count": updated,
            "unassigned_voter_ids": voters,
            "message": "Voters unassigned successfully"
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unassign_voters(request):

    if request.method != "POST":
        return Response({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        body = request.data

        voter_ids = body.get("voter_ids", [])

        if not voter_ids:
            return Response({
                "status": False,
                "message": "voter_ids are required"
            }, status=400)

        with transaction.atomic():
            updated_count = (
                VoterList.objects
                .filter(
                    voter_list_id__in=voter_ids,
                    user__isnull=False      # only assigned voters
                )
                .update(user=None)
            )

        return Response({
            "status": True,
            "unassigned_count": updated_count,
            "message": "Voters unassigned successfully"
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unassign_all_voters_of_karyakarta(request):

    try:
        body = request.data
        karyakarta_user_id = body.get("karyakarta_user_id")

        if not karyakarta_user_id:
            return Response({
                "status": False,
                "message": "karyakarta_user_id is required"
            }, status=400)

        try:
            karyakarta = VoterUserMaster.objects.get(user_id=karyakarta_user_id)
        except VoterUserMaster.DoesNotExist:
            return Response({
                "status": False,
                "message": "Karyakarta not found"
            }, status=404)

        with transaction.atomic():
            updated = (
                VoterList.objects
                .filter(user=karyakarta)
                .update(user=None)
            )

        return Response({
            "status": True,
            "unassigned_count": updated,
            "message": "All voters unassigned from karyakarta"
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)
