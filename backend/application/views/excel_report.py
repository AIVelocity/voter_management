from django.http import HttpResponse
from datetime import date
from openpyxl import Workbook
from django.utils.timezone import now
from ..models import (
    VoterUserMaster,
    VoterRelationshipDetails,
    ActivityLog
)
import csv
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.renderers import BaseRenderer
from .view_utils import build_voter_queryset
import pandas as pd
from io import BytesIO

class Echo:
    def write(self, value):
        return value


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
            .select_related("tag_id", "occupation", "cast", "religion", "user")
            .filter(user=user, check_progress_date=report_date)
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
        # safely extract voter ids
        if df1.empty:
            voter_ids = []
        else:
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
        # Ensure both dataframes have the expected key column so merge doesn't fail
        expected_voter_cols = [
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
        ]

        if "voter_list_id" not in df1.columns:
            df1 = pd.DataFrame(columns=expected_voter_cols)

        if "voter_list_id" not in df2.columns:
            df2 = pd.DataFrame(columns=["voter_list_id", "related_voter__voter_name_eng", "relation_with_voter"])

        merged_df = df1.merge(
                            df2,
                            on="voter_list_id",
                            how="left"
                        )
        
        # Rename merged_df columns to meaningful names
        merged_df.rename(columns={
            "voter_list_id": "ID",
            "voter_id": "Voter ID",
            "sr_no": "Serial No",
            "voter_name_eng": "Voter Name (English)",
            "voter_name_marathi": "Voter Name (Marathi)",
            "current_address": "Current Address",
            "mobile_no": "Mobile",
            "alternate_mobile1": "Alternate Mobile 1",
            "alternate_mobile2": "Alternate Mobile 2",
            "kramank": "Kramank",
            "address_line1": "Address Line 1",
            "age_eng": "Age",
            "gender_eng": "Gender",
            "ward_no": "Ward No",
            "location": "Location",
            "badge": "Badge",
            "tag_id": "Tag",
            "occupation": "Occupation",
            "cast": "Caste",
            "religion": "Religion",
            "comments": "Comments",
            "check_progress_date": "Check Progress Date",
            "related_voter__voter_name_eng": "Related Voter Name",
            "relation_with_voter": "Relation",
        }, inplace=True)
        
        # Drop the ID column after rename
        merged_df = merged_df.drop(columns=["ID"], errors='ignore')

        from datetime import datetime, time
        from django.utils.timezone import make_aware, get_current_timezone

        tz = get_current_timezone()

        start_dt = make_aware(datetime.combine(report_date, time.min), tz)
        end_dt   = make_aware(datetime.combine(report_date, time.max), tz)

        # Query logs for this user on the report date, regardless of whether voters exist
        logs_qs = (
            ActivityLog.objects
            .filter(
                user=user,
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
        
        # Rename logs_df columns to meaningful names
        logs_df.rename(columns={
            "voter__voter_name_eng": "Voter Name",
            "voter__voter_id": "Voter ID",
            "action": "Action",
            "user__first_name": "User First Name",
            "user__last_name": "User Last Name",
            "old_data": "Old Data",
            "new_data": "New Data",
            "created_at": "Timestamp",
        }, inplace=True)

        buffer = BytesIO()
        from django.utils.timezone import now
        # Generate meaningful filename with user and date
        user_name = f"{user.first_name}_{user.last_name}".replace(" ", "_") if user.first_name or user.last_name else f"user_{user.user_id}"
        timestamp = now().strftime("%Y%m%d_%H%M%S")

        filename = f"voter_report_{user_name}_{timestamp}.xlsx"

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            merged_df.to_excel(writer, sheet_name="Voters Data", index=False)
            logs_df.to_excel(writer, sheet_name="Change Logs", index=False)

        buffer.seek(0)

        return Response(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        return Response({"status": False, "error": str(e)}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([ExcelRenderer])
def voters_export(request):

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

        if user.role.role_name in ["SuperAdmin", "Admin"]:
            qs = (
                build_voter_queryset(request,user)
                .select_related("tag_id", "occupation", "cast", "religion", "user")
                .order_by("sr_no")
            )
        else:
            qs = (
                build_voter_queryset(request,user)
                .select_related("tag_id", "occupation", "cast", "religion", "user")
                .filter(user=user)
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
        # safely extract voter ids
        if df1.empty:
            voter_ids = []
        else:
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
        # Ensure both dataframes have the expected key column so merge doesn't fail
        expected_voter_cols = [
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
        ]

        if "voter_list_id" not in df1.columns:
            df1 = pd.DataFrame(columns=expected_voter_cols)

        if "voter_list_id" not in df2.columns:
            df2 = pd.DataFrame(columns=["voter_list_id", "related_voter__voter_name_eng", "relation_with_voter"])

        merged_df = df1.merge(
                            df2,
                            on="voter_list_id",
                            how="left"
                        )
        
        # Rename merged_df columns to meaningful names
        merged_df.rename(columns={
            "voter_list_id": "ID",
            "voter_id": "Voter ID",
            "sr_no": "Serial No",
            "voter_name_eng": "Voter Name (English)",
            "voter_name_marathi": "Voter Name (Marathi)",
            "current_address": "Current Address",
            "mobile_no": "Mobile",
            "alternate_mobile1": "Alternate Mobile 1",
            "alternate_mobile2": "Alternate Mobile 2",
            "kramank": "Kramank",
            "address_line1": "Address Line 1",
            "age_eng": "Age",
            "gender_eng": "Gender",
            "ward_no": "Ward No",
            "location": "Location",
            "badge": "Badge",
            "tag_id": "Tag",
            "occupation": "Occupation",
            "cast": "Caste",
            "religion": "Religion",
            "comments": "Comments",
            "check_progress_date": "Check Progress Date",
            "related_voter__voter_name_eng": "Related Voter Name",
            "relation_with_voter": "Relation",
        }, inplace=True)
        
        # Drop the ID column after rename
        merged_df = merged_df.drop(columns=["ID"], errors='ignore')

        buffer = BytesIO()
        from django.utils.timezone import now
        # Generate meaningful filename with user and date
        user_name = f"{user.first_name}_{user.last_name}".replace(" ", "_") if user.first_name or user.last_name else f"user_{user.user_id}"
        timestamp = now().strftime("%Y%m%d_%H%M%S")

        filename = f"voter_report_{user_name}_{timestamp}.xlsx"

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            merged_df.to_excel(writer, sheet_name="Voters Data", index=False)

        buffer.seek(0)

        return Response(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        return Response({"status": False, "error": str(e)}, status=400)