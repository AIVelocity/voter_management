
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterList
import json
import re


def normalize_mobile(number):
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    return digits[-10:] if len(digits) >= 10 else None

from rest_framework_simplejwt.tokens import AccessToken
from ..models import VoterUserMaster
import json
import re

def normalize_phone(number):
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    return digits[-10:] if len(digits) >= 10 else None


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def match_contacts_with_users(request):

    if request.method != "POST":
        return Response(
            {"status": False, "message": "POST method required"},
            status=405
        )

    # -------- AUTH --------
    auth_header = request.headers.get("Authorization")
    user_id = None

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = AccessToken(auth_header.split(" ")[1])
            user_id = token.get("user_id")
        except Exception:
            pass

    if not user_id:
        return Response(
            {"status": False, "message": "Unauthorized"},
            status=401
        )

    # -------- READ BODY --------
    try:
        body = request.data
        contacts = body.get("contacts", [])
    except json.JSONDecodeError:
        return Response(
            {"status": False, "message": "Invalid JSON"},
            status=400
        )

    if not isinstance(contacts, list):
        return Response(
            {"status": False, "message": "contacts must be a list"},
            status=400
        )

    # -------- EXTRACT NUMBERS --------
    contact_map = []   # keeps contact → number mapping
    all_numbers = set()

    for contact in contacts:
        display_name = contact.get("displayName")
        phone_entries = contact.get("phoneNumbers", [])

        for p in phone_entries:
            normalized = normalize_phone(p.get("number"))
            if normalized:
                all_numbers.add(normalized)
                contact_map.append({
                    "display_name": display_name,
                    "mobile_no": normalized
                })

    if not all_numbers:
        return Response({
            "status": True,
            "matched": [],
            "count": 0
        })

    # -------- DB MATCH --------
    users = (
        VoterUserMaster.objects
        .filter(mobile_no__in=all_numbers)
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no"
        )
    )

    user_map = {u["mobile_no"]: u for u in users}

    # -------- BUILD RESPONSE --------
    matched_contacts = []

    for item in contact_map:
        user = user_map.get(item["mobile_no"])
        if user:
            matched_contacts.append({
                "contact_name": item["display_name"],
                "mobile_no": item["mobile_no"],
                "user_id": user["user_id"],
                "first_name": user["first_name"],
                "last_name": user["last_name"]
            })

    return Response({
        "status": True,
        "count": len(matched_contacts),
        "matched": matched_contacts
    })
