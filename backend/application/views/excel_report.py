from django.http import HttpResponse
from datetime import date
from openpyxl import Workbook
from django.utils.timezone import now
from ..models import (
    VoterUserMaster,
    VoterRelationshipDetails,
    ActivityLog,
    VoterList
)
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.renderers import BaseRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .view_utils import build_voter_queryset
import json
from collections import defaultdict
import pandas as pd
from io import BytesIO

class ExcelRenderer(BaseRenderer):
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    format = "xlsx"
    charset = None
    render_style = "binary"

    def render(self, data, media_type=None, renderer_context=None):
        return data

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([ExcelRenderer])
def export_voters_excel(request):

    try:
        # -------- GET USER & ROLE --------
        user = request.user
        
        if not user or not user.is_authenticated:
            return Response(
                {"status": False, "message": "Unauthorized"},
                status=401
            )

        try:
            user = (
                VoterUserMaster.objects
                .select_related("role")
                .get(user_id=user.user_id)
            )
        except VoterUserMaster.DoesNotExist:
            return Response(
                {"status": False, "message": "User not found"},
                status=404
            )
        # ------------------ READ REPORT DATE ------------------
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

        # ------------------ WORKBOOK ------------------
        # wb = Workbook()
        # ws_voters = wb.active
        # ws_voters.title = "Voters Data"

        # ------------------ BUILD VOTER QUERYSET ------------------
        qs = (
            build_voter_queryset(request,user)
            .select_related("tag_id", "occupation", "cast", "religion")
            .order_by("sr_no")
        )
        df1 = pd.DataFrame.from_records(
                qs.values(
                    "voter_list_id",
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
                    "tag_id",
                    "occupation",
                    "cast",
                    "religion",
                    "comments",
                    "check_progress_date",
                )
            )
        # ------------------ FAMILY DATA ------------------
        # voter_ids = list(qs.values_list("voter_list_id", flat=True))
        voter_ids = list(df1['voter_list_id'])

        relations = VoterRelationshipDetails.objects.filter(
            voter_id__in=voter_ids
        ).select_related("related_voter")
        
        df2 = pd.DataFrame.from_records(
                relations.values(
                    "voter_id",
                    "related_voter__voter_name_eng",
                    "relation_with_voter"
                )
            )
        rename_cols = {'voter_id':'voter_list_id'}
        df2.rename(columns=rename_cols, inplace=True)
        
        merged_df = df1.merge(
                            df2,
                            on="voter_list_id",
                            how="left"
                        )

        from datetime import datetime, time
        from django.utils.timezone import make_aware, get_current_timezone

        tz = get_current_timezone()

        start_dt = make_aware(datetime.combine(report_date, time.min), tz)
        end_dt   = make_aware(datetime.combine(report_date, time.max), tz)

        logs_qs = (
            ActivityLog.objects
            .filter(
                voter__in=voter_ids,
                user=user,                     # only this user
                created_at__range=(start_dt, end_dt)  # only this date
            )
            .select_related("user", "voter")
            .order_by("created_at")           # chronological
        )
        
        logs_df = pd.DataFrame.from_records(
                logs_qs.values(
                    "voter__voter_name_eng",
                    "voter__voter_id",
                    "action",
                    "user__first_name",
                    "user__last_name",
                    "old_data",
                    "new_data",
                    "created_at"
                )
            )

        buffer = BytesIO()

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            merged_df.to_excel(writer, sheet_name="Voters Data", index=False)
            logs_df.to_excel(writer, sheet_name="Change Logs", index=False)

        buffer.seek(0)

        return Response(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="report.xlsx"'
            }
        )

    except Exception as e:
        return Response({"status": False, "error": str(e)}, status=400)
