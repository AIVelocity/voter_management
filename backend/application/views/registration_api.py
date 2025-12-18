from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from ..models import VoterUserMaster, UploadedLoginExcel
import json
import re
from django.db import transaction
from openpyxl import load_workbook
import base64
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import io
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import parser_classes



def is_valid_mobile(mobile):
    # Allows only exactly 10 digits
    pattern = r'^[6-9]\d{9}$'
    return bool(re.match(pattern, mobile))

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password
from application.models import VoterUserMaster
import re

def is_valid_mobile(mobile):
    return bool(re.match(r'^[6-9]\d{9}$', mobile))


@api_view(["POST"])
@permission_classes([AllowAny])
def registration(request):
    data = request.data

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    mobile_no = data.get("mobile_no")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if not first_name:
        return Response({"status": False, "message": "First Name is required"}, status=400)

    if not last_name:
        return Response({"status": False, "message": "Last Name is required"}, status=400)

    if not mobile_no or not is_valid_mobile(mobile_no):
        return Response({"status": False, "message": "Invalid mobile number"}, status=400)

    if not password or password != confirm_password:
        return Response({"status": False, "message": "Passwords do not match"}, status=400)

    if VoterUserMaster.objects.filter(mobile_no=mobile_no).exists():
        return Response({"status": False, "message": "Mobile already registered"}, status=400)

    user = VoterUserMaster.objects.create(
        first_name=first_name,
        last_name=last_name,
        mobile_no=mobile_no,
        password=make_password(password),
        role_id=3
    )

        # ---------- RESPONSE ----------
    return Response({
            "status": True,
            "message": "Registration successful",
            "data": {
                "user_id": user.user_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_no": user.mobile_no
                # "role_id": user.role.role_id
            }
        })        
        
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from openpyxl import load_workbook
import io

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_login_credentials_excel(request):

    if request.method != "POST":
        return Response(
            {"status": False, "message": "POST required"},
            status=405
        )

    try:
        excel_file = request.FILES.get("file")

        if not excel_file:
            return Response(
                {"status": False, "message": "Excel file is required"},
                status=400
            )

        file_name = excel_file.name
        file_bytes = excel_file.read()

        # -------- LOAD EXCEL --------
        wb = load_workbook(io.BytesIO(file_bytes))
        sheet = wb.active

        raw_headers = [
            str(cell.value).strip().lower()
            for cell in sheet[1]
            if cell.value
        ]

        required_headers = {
            "first name",
            "last name",
            "mobile number",
            "password"
        }

        if not required_headers.issubset(set(raw_headers)):
            return Response(
                {
                    "status": False,
                    "message": "Invalid Excel format",
                    "required_columns": list(required_headers)
                },
                status=400
            )

        created = 0
        skipped = 0
        errors = []

        # -------- SAVE EXCEL META --------
        uploaded_excel = UploadedLoginExcel.objects.create(
            file_name=file_name
        )

        header_index = {h: i for i, h in enumerate(raw_headers)}

        # -------- PROCESS ROWS --------
        with transaction.atomic():
            for row_no, row in enumerate(
                sheet.iter_rows(min_row=2, values_only=True),
                start=2
            ):

                first_name = row[header_index["first name"]]
                last_name = row[header_index["last name"]]
                mobile_no = row[header_index["mobile number"]]
                password = row[header_index["password"]]

                mobile_no = str(mobile_no).strip() if mobile_no else None

                if not first_name or not mobile_no or not password:
                    skipped += 1
                    errors.append(f"Row {row_no}: missing required fields")
                    continue

                if VoterUserMaster.objects.filter(mobile_no=mobile_no).exists():
                    skipped += 1
                    errors.append(f"Row {row_no}: mobile already exists ({mobile_no})")
                    continue

                VoterUserMaster.objects.create(
                    first_name=str(first_name).strip(),
                    last_name=str(last_name).strip() if last_name else "",
                    mobile_no=mobile_no,
                    password=make_password(str(password)),
                    role_id=3
                )

                created += 1

        uploaded_excel.created_count = created
        uploaded_excel.skipped_count = skipped
        uploaded_excel.save()

        return Response({
            "status": True,
            "message": "Excel imported successfully",
            "excel_id": uploaded_excel.id,
            "created_users": created,
            "skipped_rows": skipped,
            "errors": errors
        })

    except Exception as e:
        return Response(
            {"status": False, "error": str(e)},
            status=500
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_uploaded_login_excels(request):
    excels = UploadedLoginExcel.objects.order_by("-uploaded_at")

    data = []
    for e in excels:
        data.append({
            "excel_id": e.id,
            "file_name": e.file_name,
            "uploaded_at": e.uploaded_at.strftime("%d-%m-%Y %I:%M %p"),
            "created_users": e.created_count,
            "skipped_rows": e.skipped_count
        })

    return Response({
        "status": True,
        "count": len(data),
        "data": data
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_login_excel(request, excel_id):
    excel = get_object_or_404(UploadedLoginExcel, id=excel_id)

    base64_data = excel.file_base64

    # strip prefix if ever present
    if "," in base64_data:
        base64_data = base64_data.split(",")[1]

    file_bytes = base64.b64decode(base64_data)

    response = HttpResponse(
        file_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    filename = excel.file_name
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(file_bytes)

    return response
