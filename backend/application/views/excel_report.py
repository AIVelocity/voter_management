from django.http import HttpResponse
from django.utils.timezone import now
from ..models import (
    VoterUserMaster,
    VoterRelationshipDetails,
    ActivityLog
)
import csv
from datetime import date, datetime, time
from django.utils.timezone import make_aware, get_current_timezone, now
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.renderers import BaseRenderer
from .view_utils import build_voter_queryset,format_change_data
from collections import defaultdict

class Echo:
    def write(self, value):
        return value

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_voters_excel(request):

    try:
        # ------------------ USER ------------------
        user = request.user
        user = VoterUserMaster.objects.select_related("role").get(
            user_id=user.user_id
        )

        # ------------------ REPORT DATE ------------------
        report_date = request.GET.get("report_date")
        if not report_date:
            return Response(
                {"status": False, "message": "report_date is required (YYYY-MM-DD)"},
                status=400
            )

        try:
            report_date = date.fromisoformat(report_date)
        except ValueError:
            return Response(
                {"status": False, "message": "Invalid report_date format"},
                status=400
            )

        # ------------------ QUERYSET ------------------
        if user.role.role_name in ["SuperAdmin", "Admin"]:
            qs = (
                build_voter_queryset(request, user)
                .filter(check_progress_date=report_date)
                .order_by("sr_no")
            )
        else:
            qs = (
                build_voter_queryset(request, user)
                .filter(user=user, check_progress_date=report_date)
                .order_by("sr_no")
            )

        # ------------------ RESPONSE (UTF-8 BOM FOR EXCEL) ------------------
        filename = f"voter_report_{user.first_name}_{user.last_name}_{now().strftime('%Y%m%d_%H%M%S')}.csv"

        response = HttpResponse(
            content_type="text/csv; charset=utf-8-sig"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        # THIS LINE FIXES MARATHI IN EXCEL
        response.write("\ufeff")

        writer = csv.writer(response)

        # ==========================================================
        # =============== SECTION 1 : VOTERS DATA ==================
        # ==========================================================
        writer.writerow(["VOTERS DATA"])
        writer.writerow([
            "Voter ID",
            "Serial No",
            "Voter Name (English)",
            "Voter Name (Marathi)",
            "Current Address",
            "Mobile",
            "Alternate Mobile 1",
            "Alternate Mobile 2",
            "Kramank",
            "Address Line 1",
            "Age",
            "Gender",
            "Ward No",
            "Location",
            "Badge",
            "Tag",
            "Occupation",
            "Caste",
            "Religion",
            "Comments",
            "Check Progress Date",
        ])

        for row in qs.values_list(
            "voter_id",
            "sr_no",
            "voter_name_eng",
            "voter_name_marathi",
            "current_address",
            "mobile_no",
            "alternate_mobile1",
            "alternate_mobile2",
            "kramank",
            "address_line1",
            "age_eng",
            "gender_eng",
            "ward_no",
            "location",
            "badge",
            "tag_id__tag_name",
            "occupation__occupation_name",
            "cast__caste_name",
            "religion__religion_name",
            "comments",
            "check_progress_date",
        ).iterator(chunk_size=5000):
            writer.writerow(row)

        # ==========================================================
        # =============== SECTION 2 : CHANGE LOGS ===================
        # ==========================================================
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["CHANGE LOGS"])

        writer.writerow([
            "Voter Name",
            "Voter ID",
            "Action",
            "User First Name",
            "User Last Name",
            "Old Data",
            "New Data",
            "Timestamp",
        ])

        tz = get_current_timezone()
        start_dt = make_aware(datetime.combine(report_date, time.min), tz)
        end_dt   = make_aware(datetime.combine(report_date, time.max), tz)

        logs_qs = (
            ActivityLog.objects
            .filter(
                user=user,
                created_at__range=(start_dt, end_dt)
            )
            .order_by("created_at")
        )

        for (
            voter_name,
            voter_id,
            action,
            user_first,
            user_last,
            old_data,
            new_data,
            created_at,
        ) in logs_qs.values_list(
            "voter__voter_name_eng",
            "voter__voter_id",
            "action",
            "user__first_name",
            "user__last_name",
            "old_data",
            "new_data",
            "created_at",
        ).iterator(chunk_size=5000):

            writer.writerow([
                voter_name,
                voter_id,
                action,
                user_first,
                user_last,
                format_change_data(old_data),  
                format_change_data(new_data),   
                created_at,
            ])


        return response

    except Exception as e:
        return Response(
            {"status": False, "error": str(e)},
            status=400
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def voters_export(request):

    # ------------------ USER & ROLE ------------------
    user = request.user
    user = VoterUserMaster.objects.select_related("role").get(
        user_id=user.user_id
    )

    if user.role.role_name in ["SuperAdmin", "Admin"]:
        qs = build_voter_queryset(request, user)
    else:
        qs = build_voter_queryset(request, user).filter(user=user)

    qs = qs.order_by("sr_no")

    # ------------------ RESPONSE (STREAMING CSV) ------------------
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    filename = f"voter_report_{user.first_name}{user.last_name}_{now().strftime('%Y%m%d_%H%M%S')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)

    # ------------------ HEADERS ------------------
    writer.writerow([
        "Voter ID",
        "Serial No",
        "Voter Name (English)",
        "Voter Name (Marathi)",
        "Current Address",
        "Mobile",
        "Alternate Mobile 1",
        "Alternate Mobile 2",
        "Kramank",
        "Address Line 1",
        "Age",
        "Gender",
        "Ward No",
        "Location",
        "Badge",
        "Tag",
        "Occupation",
        "Caste",
        "Religion",
        "Comments",
        "Check Progress Date",
        "Father",
        "Mother",
        "Sibling",
        "Child",
    ])

    # ------------------ RELATION MAP ------------------
    relation_map = defaultdict(lambda: {
        "father": None,
        "mother": None,
        "sibling": [],
        "child": [],
    })

    relations_qs = (
        VoterRelationshipDetails.objects
        .select_related("related_voter")
        .filter(
            voter_id__in=qs.values_list("voter_list_id", flat=True)
        )
    )

    for r in relations_qs:
        rel = (r.relation_with_voter or "").lower()
        name = r.related_voter.voter_name_eng if r.related_voter else None
        if not name:
            continue

        if rel == "father":
            relation_map[r.voter_id]["father"] = name
        elif rel == "mother":
            relation_map[r.voter_id]["mother"] = name
        elif rel in ("brother", "sister"):
            relation_map[r.voter_id]["sibling"].append(name)
        elif rel in ("son", "daughter"):
            relation_map[r.voter_id]["child"].append(name)

    # ------------------ WRITE ROWS (FAST STREAMING) ------------------
    for row in qs.values_list(
        "voter_id",
        "sr_no",
        "voter_name_eng",
        "voter_name_marathi",
        "current_address",
        "mobile_no",
        "alternate_mobile1",
        "alternate_mobile2",
        "kramank",
        "address_line1",
        "age_eng",
        "gender_eng",
        "ward_no",
        "location",
        "badge",
        "tag_id__tag_name",
        "occupation__occupation_name",
        "cast__caste_name",
        "religion__religion_name",
        "comments",
        "check_progress_date",
        "voter_list_id",
    ).iterator(chunk_size=5000):

        *data, voter_list_id = row
        rel = relation_map.get(voter_list_id, {})

        writer.writerow(list(data) + [
            rel.get("father"),
            rel.get("mother"),
            ", ".join(rel.get("sibling", [])) or None,
            ", ".join(rel.get("child", [])) or None,
        ])

    return response
