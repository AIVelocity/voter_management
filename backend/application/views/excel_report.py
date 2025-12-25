from django.http import HttpResponse
from openpyxl import Workbook
from django.utils.timezone import now
from ..models import VoterList,VoterRelationshipDetails
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.renderers import BaseRenderer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Min, Max
from .view_utils import build_voter_queryset

class ExcelRenderer(BaseRenderer):
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
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
        wb = Workbook()
        wb_data = wb.active
        wb_data.title = "Voters Data"

        # ---- READ DATES FROM QUERY PARAMS ----
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        # ---- BUILD BASE QUERYSET (ALL FILTERS FROM FRONTEND) ----
        qs = build_voter_queryset(request)

        # ---- AUTO DATE RANGE (FIRST → LAST) ----
        if not from_date or not to_date:
            date_range = qs.aggregate(
                min_date=Min("check_progress_date"),
                max_date=Max("check_progress_date")
            )

            if not date_range["min_date"] or not date_range["max_date"]:
                return Response(
                    {
                        "status": True,
                        "message": "No data available for export",
                        "count": 0
                    }
                )

            from_date = date_range["min_date"].date()
            to_date = date_range["max_date"].date()

        # ---- APPLY DATE FILTER + OPTIMIZE ----
        qs = (
            qs
            .select_related(
                "tag_id",
                "occupation",
                "cast",
                "religion"
            )
            .filter(
                check_progress_date__date__range=[from_date, to_date]
            )
            .order_by("sr_no")
        )

        # ---- FAMILY DATA ----
        voter_ids = list(qs.values_list("voter_list_id", flat=True))
        relations = VoterRelationshipDetails.objects.filter(
            voter_id__in=voter_ids
        )

        from collections import defaultdict
        family_map = defaultdict(lambda: {
            "father": None,
            "mother": None,
            "spouse": None,
            "siblings": [],
            "children": [],
        })

        for r in relations:
            fam = family_map[r.voter_id]
            if r.relation_type == "Father":
                fam["father"] = r.name
            elif r.relation_type == "Mother":
                fam["mother"] = r.name
            elif r.relation_type == "Spouse":
                fam["spouse"] = r.name
            elif r.relation_type == "Sibling":
                fam["siblings"].append(r.name)
            elif r.relation_type == "Child":
                fam["children"].append(r.name)

        # ---- HEADERS ----
        wb_data.append([
            "Voter ID", "SR No", "Voter Name English", "Voter Name Marathi",
            "Address", "Mobile", "Alt Mobile 1", "Alt Mobile 2",
            "Kramank", "Full Address", "Age", "Gender",
            "Ward", "Location", "Badge", "Tag",
            "Occupation", "Caste", "Religion",
            "Father", "Mother", "Spouse",
            "Siblings", "Children",
            "Comments",
            "Tag Updated By", "Tag Updated At",
            "Comment Updated By", "Comment Updated At",
            "Check Progress Date"
        ])

        # ---- ROWS ----
        for voter in qs:
            fam = family_map[voter.voter_list_id]

            wb_data.append([
                voter.voter_id,
                voter.sr_no,
                voter.voter_name_eng,
                voter.voter_name_marathi,
                voter.current_address,
                voter.mobile_no,
                voter.alternate_mobile1,
                voter.alternate_mobile2,
                voter.kramank,
                voter.address_line1,
                voter.age_eng,
                voter.gender_eng,
                voter.ward_no,
                voter.location,
                voter.badge,
                voter.tag_id.tag_name if voter.tag_id else None,
                voter.occupation.name if voter.occupation else None,
                voter.cast.name if voter.cast else None,
                voter.religion.name if voter.religion else None,
                fam["father"],
                fam["mother"],
                fam["spouse"],
                ", ".join(fam["siblings"]),
                ", ".join(fam["children"]),
                voter.comments,
                voter.tag_last_updated_by,
                voter.tag_last_updated_at,
                voter.comment_last_updated_by,
                voter.comment_last_updated_at,
                voter.check_progress_date,
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="voter_export_{now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        )

        wb.save(response)
        return response

    except Exception as e:
        return Response({"status": False, "error": str(e)}, status=500)
