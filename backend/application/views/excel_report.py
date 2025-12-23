from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum, IntegerField
from django.db.models.functions import Cast
from openpyxl import Workbook
from django.utils.timezone import now
from ..models import VoterList
import json
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.renderers import BaseRenderer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class ExcelRenderer(BaseRenderer):
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    format = "xlsx"
    charset = None
    render_style = "binary"

    def render(self, data, media_type=None, renderer_context=None):
        return data

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@renderer_classes([ExcelRenderer])
def export_voters_excel(request):

    if request.method != "POST":
        return Response(
            {"status": False, "message": "POST method required"},
            status=405
        )

    try:
        body = request.data

        fields = body.get("fields", [])
        filters = body.get("filters", {})
        summary = body.get("summary", {})

        if not fields:
            return Response(
                {"status": False, "message": "fields are required"},
                status=400
            )

        # ---- Validate fields ----
        valid_fields = {f.name for f in VoterList._meta.fields}
        invalid = [f for f in fields if f not in valid_fields]

        if invalid:
            return Response(
                {"status": False, "invalid_fields": invalid},
                status=400
            )

        qs = VoterList.objects.filter(**filters)

        # ---- Create Workbook ----
        wb = Workbook()

        # ================= DATA SHEET =================
        ws_data = wb.active
        ws_data.title = "Voters Data"

        ws_data.append([f.replace("_", " ").title() for f in fields])

        for row in qs.values(*fields):
            ws_data.append([row.get(f) for f in fields])

        # ================= SUMMARY SHEET =================
        ws_summary = wb.create_sheet("Summary")

        # COUNT
        if summary.get("count"):
            ws_summary.append(["Total Records", qs.count()])
            ws_summary.append([])

        # SUM (SAFE)
        for field in summary.get("sum", []):
            if field not in valid_fields:
                continue

            try:
                # Try normal SUM (numeric fields)
                result = qs.aggregate(total=Sum(field))["total"]
            except Exception:
                # Fallback: cast VARCHAR → INTEGER
                try:
                    result = qs.aggregate(
                        total=Sum(Cast(field, IntegerField()))
                    )["total"]
                except Exception:
                    result = None

            if result is not None:
                ws_summary.append([f"Sum of {field}", result])

        ws_summary.append([])

        # GROUP BY
        for field in summary.get("group_by", []):
            if field not in valid_fields:
                continue

            ws_summary.append([f"{field.title()} Wise Count"])
            ws_summary.append([field.title(), "Count"])

            grouped = qs.values(field).annotate(
                total=Count("voter_list_id")
            )

            for g in grouped:
                ws_summary.append([g[field], g["total"]])

            ws_summary.append([])

        # ---- Response ----
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"voter_export_{now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        wb.save(response)
        return response

    except Exception as e:
        return Response(
            {"status": False, "error": str(e)},
            status=500
        )
