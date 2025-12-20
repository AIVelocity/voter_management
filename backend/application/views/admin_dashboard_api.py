from ..models import VoterList,VoterUserMaster
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, OuterRef
from django.db import transaction
import json
from django.core.paginator import Paginator, EmptyPage
from collections import defaultdict
from rest_framework_simplejwt.tokens import AccessToken
from .voters_info_api import split_marathi_name
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):

    user = None
    user_id = None
    
    try:
        auth_header = request.headers.get("Authorization")
        lang = request.headers.get("lang", "en")
    
        if auth_header and auth_header.startswith("Bearer "):
            token_str = auth_header.split(" ")[1]
            token = AccessToken(token_str)
            user_id = token.get("user_id")
    except Exception:
        pass
    
    # user = None
    if user_id:
        try:
            user = VoterUserMaster.objects.get(user_id=user_id)
        except VoterUserMaster.DoesNotExist:
            user = None
    
    assigned_count = VoterList.objects.filter(user=user).count()

    visited_count = VoterList.objects.filter(
        user=user_id,
        check_progress_date__isnull=False
    ).count()

    # sr_range = VoterList.objects.filter(user=user).aggregate(
    #     min_sr=Min("sr_no"),
    #     max_sr=Max("sr_no")
    # )

    pending_count = assigned_count - visited_count
    
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
    
    return Response({
        "SUCCESS": True,
        "data" : { 
                "user_first_name": user.first_name, 
                "name": f"{user.first_name} {user.last_name}",
                "mobile": user.mobile_no,
                "assigned": assigned_count,
                "visited": visited_count,
                "pending": pending_count,
            
                "golden_voter":golden_color_tags,
                "guaranteed_voter" :green_color_tags,
                "unsure_voter" : orange_color_tags,
                "red_color_tags" : red_color_tags,
                "total_voters": total_voters,  # convert queryset to list
                "karyakartas": list(karyakarta_users),
                "daywise_check_progress": list(daywise),
                "total_visited" : total_visited,
                "week_difference": difference,
                "this_week": this_week_count,
                "last_week": last_week_count 
        }
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def volunteer_allocation_panel(request):

    total_voters = VoterList.objects.count()

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

    assigned_karyakarta_list = [
        k for k in karyakarta_list if k["assigned_count"] > 0
    ]

    # ---------------- THIRD SCREEN (UNASSIGNED) ----------------

    unassigned_karyakarta_list = [
        k for k in karyakarta_list if k["assigned_count"] == 0
    ]

    return Response({
        "SUCCESS" :True,
        "data":{ 
            "summary": {
                "total_voters": total_voters,
                "total_karyakartas": total_karyakartas,
                "assigned_karyakartas": assigned_karyakartas,
                "unassigned_karyakartas": unassigned_karyakartas
                },
                
                # ---------- FIRST SCREEN ----------
                "allocated_first_screen_karyakartas": karyakarta_list,

                # ---------- SECOND SCREEN ----------
                "allocated_second_screen_karyakartas": assigned_karyakarta_list,
                
                # ---------- THIRD SCREEN (UNASSIGNED) ---------
                "allocated_third_screen_karyakartas": unassigned_karyakarta_list
            }
        }
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unassigned_voters(request):
    lang = request.headers.get("Accept-Language", "en")
    is_marathi = lang.lower().startswith("mr")

    # -------- GET PARAMS --------
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 50)) 

    # -------- BASE QUERY --------
    queryset = (
        VoterList.objects
        .filter(user__isnull=True)
        .values(
            "serial_number",
            "voter_list_id",
            # "sr_no",
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
        voters = []

        for v in page_obj.object_list:
            if is_marathi:
                first_name, middle_name, last_name = split_marathi_name(
                    v.get("voter_name_marathi")
                )

                voters.append({
                    "serial_number": v["serial_number"],
                    "voter_list_id": v["voter_list_id"],
                    "voter_id": v["voter_id"],

                    "voter_name": v["voter_name_marathi"],
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,

                    "mobile_no": v["mobile_no"],
                    "ward_no": v["ward_no"],
                    "age": v["age"],
                    "gender": v.get("gender"),   # Marathi gender
                    "badge": v["badge"],
                    "location": v["location"],
                })

            else:
                voters.append({
                    "serial_number": v["serial_number"],
                    "voter_list_id": v["voter_list_id"],
                    "voter_id": v["voter_id"],

                    "voter_name": v["voter_name_eng"],
                    "first_name": v["first_name"],
                    "middle_name": v["middle_name"],
                    "last_name": v["last_name"],

                    "mobile_no": v["mobile_no"],
                    "ward_no": v["ward_no"],
                    "age": v["age"],
                    "gender": v["gender_eng"],
                    "badge": v["badge"],
                    "location": v["location"],
                })

    except EmptyPage:
        return Response({
            "status": True,
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "voters": []
        })

    return Response({
        "SUCCESS": True,
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "voters": voters
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
            "SUCCESS": True,
            "assigned_count": updated_count,
            "message": "Voters assigned successfully"
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)


# def auto_select_unassigned_voters(request):

#     try:
#         count = int(request.GET.get("count", 0))
#     except ValueError:
#         return Response({
#             "status": False,
#             "message": "Invalid count"
#         }, status=400)

#     if count <= 0:
#         return Response({
#             "status": False,
#             "message": "Count must be greater than 0"
#         }, status=400)

#     voters = (
#         VoterList.objects
#         .filter(user__isnull=True)
#         .order_by("sr_no")
#         .values(
#             "voter_list_id",
#             "sr_no",
#             "voter_id",
#             "voter_name_eng",
#             "voter_name_marathi",
#             "mobile_no",
#             "ward_no",
#             "age",
#             "gender_eng",
#             "badge",
#             "location"
#         )[:count]
#     )

#     return Response({
#         "SUCCESS": True,
#         "requested_count": count,
#         "returned_count": len(voters),
#         "voters": list(voters),
#         "voter_ids": [v["voter_list_id"] for v in voters]
#     })
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auto_assign_unassigned_voters(request):

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
            "assigned_voter_ids": voters
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)
