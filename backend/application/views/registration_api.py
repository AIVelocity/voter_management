from django.http import JsonResponse
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

def is_valid_mobile(mobile):
    # Allows only exactly 10 digits
    pattern = r'^[6-9]\d{9}$'
    return bool(re.match(pattern, mobile))


@csrf_exempt
def registration(request):

    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "Method must be POST"
        })

    try:
        body = json.loads(request.body)

        first_name = body.get("first_name")
        last_name = body.get("last_name")
        # role_id = body.get("role_id")
        mobile_no = body.get("mobile_no")

        password = body.get("password")
        confirm_password = body.get("confirm_password")

        # ---------- VALIDATION ----------
        if not first_name:
            return JsonResponse({"status": False, "message": "First Name is required"})

        if not last_name:
            return JsonResponse({"status": False, "message": "Last Name is required"})

        # if not role_id:
        #     return JsonResponse({"status": False, "message": "Role is required"})

        if not mobile_no:
            return JsonResponse({"status": False, "message": "Mobile Number is required"})

        if not is_valid_mobile(mobile_no):
            return JsonResponse({
                "status": False,
                "message": "Mobile number must be a valid 10-digit Indian number"
            })

        if not password or not confirm_password:
            return JsonResponse({
                "status": False,
                "message": "Password and Confirm Password are required"
            })

        if password != confirm_password:
            return JsonResponse({
                "status": False,
                "message": "Password and Confirm Password do not match"
            })

        # # ---------- ROLE VALIDATION ----------
        # try:
        #     role = Roles.objects.get(role_id=role_id)
        # except Roles.DoesNotExist:
        #     return JsonResponse({"status": False, "message": "Invalid role_id"})

        # ---------- DUPLICATE MOBILE ----------
        if VoterUserMaster.objects.filter(mobile_no=mobile_no).exists():
            return JsonResponse({
                "status": False,
                "message": "Mobile number already registered"
            })

        # ---------- HASH PASSWORD ----------
        hashed_password = make_password(password)

        # ---------- SAVE USER ----------
        user = VoterUserMaster.objects.create(
            first_name=first_name,
            last_name=last_name,
            mobile_no=mobile_no,
            password=hashed_password,
            confirm_password=hashed_password,
            role_id=3
        )

        # ---------- RESPONSE ----------
        return JsonResponse({
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

    except Exception as e:
        return JsonResponse({
            "status": False,
            "error": str(e)
        })
        
        
@csrf_exempt
def upload_login_credentials_excel(request):

    if request.method != "POST":
        return JsonResponse(
            {"status": False, "message": "POST required"},
            status=405
        )

    try:
        # -------- READ JSON BODY --------
        body = json.loads(request.body)

        file_name = body.get("file_name")
        file_base64 = body.get("file_base64")

        if not file_name or not file_base64:
            return JsonResponse(
                {
                    "status": False,
                    "message": "file_name and file_base64 are required"
                },
                status=400
            )

        # -------- DECODE BASE64 --------
        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception:
            return JsonResponse(
                {"status": False, "message": "Invalid base64 file"},
                status=400
            )

        # -------- LOAD EXCEL --------
        wb = load_workbook(io.BytesIO(file_bytes))
        sheet = wb.active

        raw_headers = [
            str(cell.value).strip().lower()
            for cell in sheet[1]
        ]

        required_headers = {
            "first name",
            "last name",
            "mobile number",
            "password"
        }

        if not required_headers.issubset(set(raw_headers)):
            return JsonResponse(
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

        # -------- SAVE EXCEL RECORD --------
        uploaded_excel = UploadedLoginExcel.objects.create(
            file_name=file_name,
            file_base64=file_base64
        )

        # -------- PROCESS ROWS --------
        with transaction.atomic():
            for row_index, row in enumerate(
                sheet.iter_rows(min_row=2, values_only=True),
                start=2
            ):
                row_data = dict(zip(raw_headers, row))

                first_name = row_data.get("first name")
                last_name = row_data.get("last name")
                mobile_no = (
                    str(row_data.get("mobile number")).strip()
                    if row_data.get("mobile number") else None
                )
                password = row_data.get("password")

                if not first_name or not mobile_no or not password:
                    skipped += 1
                    errors.append(f"Row {row_index}: missing required fields")
                    continue

                if VoterUserMaster.objects.filter(mobile_no=mobile_no).exists():
                    skipped += 1
                    errors.append(f"Row {row_index}: mobile already exists ({mobile_no})")
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

        return JsonResponse({
            "status": True,
            "message": "Excel imported successfully",
            "excel_id": uploaded_excel.id,
            "created_users": created,
            "skipped_rows": skipped,
            "errors": errors
        })

    except Exception as e:
        return JsonResponse(
            {"status": False, "error": str(e)},
            status=500
        )


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

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })


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
