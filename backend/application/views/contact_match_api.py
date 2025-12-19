import re
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from django.db import transaction

from ..models import VoterList, UserVoterContact


# ------------------ NORMALIZATION ------------------

def normalize_phone(number: str) -> str | None:
    if not number:
        return None

    digits = re.sub(r"\D", "", number)

    # India-only
    if len(digits) == 10:
        return digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]

    return None


def extract_contact_name(contact: dict) -> str:
    # Android
    if contact.get("displayName"):
        return contact["displayName"]

    # iOS
    given = contact.get("givenName", "")
    family = contact.get("familyName", "")
    name = f"{given} {family}".strip()

    return name or "Unknown"


def extract_phone_numbers(contact: dict) -> list[str]:
    numbers = []

    for p in contact.get("phoneNumbers", []):
        if "number" in p:   # Android
            numbers.append(p["number"])
        elif "value" in p:  # iOS
            numbers.append(p["value"])

    return numbers


# ------------------ API ------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def match_contacts_with_users(request):

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

    data = request.data

# SUPPORT BOTH PAYLOAD TYPES
    if isinstance(data, list):
        contacts = data
    elif isinstance(data, dict):
        contacts = data.get("contacts", [])
    else:
        contacts = []
    
    if not isinstance(contacts, list):
        return Response(
            {"status": False, "message": "contacts must be a list"},
            status=400
        )

    # -------- CANONICALIZE CONTACTS --------
    canonical_contacts = {}   # mobile_no -> contact_name
    all_numbers = set()

    for contact in contacts:
        contact_name = extract_contact_name(contact)
        for raw in extract_phone_numbers(contact):
            mobile = normalize_phone(raw)
            if mobile:
                canonical_contacts[mobile] = contact_name
                all_numbers.add(mobile)

    if not all_numbers:
        return Response({"status": True, "count": 0, "matched": []})

    # -------- MATCH WITH VOTERLIST --------
    voters = (
        VoterList.objects
        .filter(mobile_no__in=all_numbers)
        .values("voter_list_id", "mobile_no", "voter_name_eng", "voter_name_marathi")
    )

    voter_map = {v["mobile_no"]: v for v in voters}

    matched = []
    to_create = []

    for mobile, contact_name in canonical_contacts.items():
        voter = voter_map.get(mobile)
        if voter:
            voter_name = (
                voter["voter_name_eng"]
                or voter["voter_name_marathi"]
            )

            matched.append({
                "mobile_no": mobile,
                "contact_name": contact_name,
                "voter_id": voter["voter_list_id"],
                "voter_name": voter_name
            })

            to_create.append(
                UserVoterContact(
                    user_id=user_id,
                    voter_id=voter["voter_list_id"],
                    contact_name=contact_name,
                    voter_name=voter_name,
                    mobile_no=mobile
                )
            )

    # -------- SAVE --------
    if to_create:
        with transaction.atomic():
            UserVoterContact.objects.bulk_create(
                to_create,
                ignore_conflicts=True
            )

    return Response({
        "status": True,
        "count": len(matched),
        "matched": matched
    })
