from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from ..models import VoterUserMaster, Roles
import json
import re


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
        
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.hashers import make_password
from openpyxl import load_workbook
from ..models import VoterUserMaster


@csrf_exempt
def upload_login_credentials_excel(request):

    if request.method != "POST":
        return JsonResponse(
            {"status": False, "message": "POST method required"},
            status=405
        )

    file = request.FILES.get("file")

    if not file:
        return JsonResponse(
            {"status": False, "message": "Excel file is required"},
            status=400
        )

    try:
        wb = load_workbook(file)
        sheet = wb.active

        # ---- Normalize headers ----
        raw_headers = [str(cell.value).strip().lower() for cell in sheet[1]]

        header_map = {
            "first name": "first_name",
            "last name": "last_name",
            "mobile number": "mobile_no",
            "password": "password",
        }

        if not set(header_map.keys()).issubset(set(raw_headers)):
            return JsonResponse({
                "status": False,
                "message": "Invalid Excel format",
                "required_columns": list(header_map.keys())
            }, status=400)


        created = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for row_index, row in enumerate(
                sheet.iter_rows(min_row=2, values_only=True),
                start=2
            ):
                excel_row = dict(zip(raw_headers, row))

                first_name = excel_row.get("first name")
                last_name = excel_row.get("last name")
                mobile_no = str(excel_row.get("mobile number")).strip() if excel_row.get("mobile number") else None
                password = excel_row.get("password")

                # ---- Validation ----
                if not first_name or not mobile_no or not password:
                    errors.append(f"Row {row_index}: missing required fields")
                    skipped += 1
                    continue

                if VoterUserMaster.objects.filter(mobile_no=mobile_no).exists():
                    errors.append(f"Row {row_index}: mobile already exists ({mobile_no})")
                    skipped += 1
                    continue

                # ---- Create user ----
                VoterUserMaster.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    mobile_no=mobile_no,
                    password=make_password(str(password)),
                    role_id=3
                )

                created += 1

        return JsonResponse({
            "status": True,
            "message": "Login credentials imported successfully",
            "created_users": created,
            "skipped_rows": skipped,
            "errors": errors
        })

    except Exception as e:
        return JsonResponse(
            {"status": False, "error": str(e)},
            status=500
        )