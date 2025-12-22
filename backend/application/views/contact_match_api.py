from django.db.models import Q
import os
import re
import json
from django.conf import settings
from datetime import datetime
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
    """
    Extracts contact name from ALL known payload formats.
    """

    if not isinstance(contact, dict):
        return "Unknown"

    # 1️Custom / simplified payload
    name = contact.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()

    # 2Android
    name = contact.get("displayName")
    if isinstance(name, str) and name.strip():
        return name.strip()

    # 3 iOS (given + family)
    given = contact.get("givenName", "")
    family = contact.get("familyName", "")
    full = f"{given} {family}".strip()
    if full:
        return full

    #  Other common fallbacks
    for key in ["fullName", "contactName", "username"]:
        value = contact.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return "Unknown"


def extract_phone_numbers(contact: dict) -> list[str]:
    """
    Extracts phone numbers from ALL known payload formats.
    """

    if not isinstance(contact, dict):
        return []

    numbers = []

    def add(num):
        if isinstance(num, str) and num.strip():
            numbers.append(num.strip())

    # 1️ Your custom payload with {id, label, number} dicts
    if isinstance(contact.get("numbers"), list):
        for item in contact["numbers"]:
            if isinstance(item, dict):
                add(item.get("number"))
            elif isinstance(item, str):
                add(item)

    # 2️ Android payload
    if isinstance(contact.get("phoneNumbers"), list):
        for item in contact["phoneNumbers"]:
            if isinstance(item, dict):
                add(item.get("number"))   # Android
                add(item.get("value"))    # iOS

    # 3️ Other possible keys
    for key in ["mobile", "phone", "phoneNumber"]:
        add(contact.get(key))

    # 4️ Raw string list fallback
    if isinstance(contact.get("phones"), list):
        for p in contact["phones"]:
            add(p)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for n in numbers:
        if n not in seen:
            seen.add(n)
            unique.append(n)

    return unique
def canonicalize_contacts(payload) -> list[dict]:
    """
    Converts ANY contact payload into a clean standard format:
    {
        "name": str,
        "numbers": [str, str, ...]
    }
    """

    contacts = []

    if isinstance(payload, list):
        raw_contacts = payload
    elif isinstance(payload, dict):
        raw_contacts = payload.get("contacts", [])
    else:
        return contacts

    for c in raw_contacts:
        name = extract_contact_name(c)
        numbers = extract_phone_numbers(c)

        if numbers:
            contacts.append({
                "name": name,
                "numbers": numbers
            })

    return contacts

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
    body = request.data
    # -------- CANONICALIZE INPUT --------
    canonical_contacts = canonicalize_contacts(body.get("data"))
    # -------- DEBUG: SAVE RAW PAYLOAD --------
    try:
        debug_dir = os.path.join(settings.BASE_DIR, "debug_payloads")
        os.makedirs(debug_dir, exist_ok=True)
    
        filename = f"contacts_user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = os.path.join(debug_dir, filename)
    
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(body.get("data"), indent=2, ensure_ascii=False))
    
    except Exception as e:
        print("Payload dump failed:", str(e))

    if not canonical_contacts:
        return Response({"status": True, "count": 0, "matched": []})

    mobile_to_name = {}
    all_numbers = set()

    for contact in canonical_contacts:
        name = contact["name"]
        for raw in contact["numbers"]:
            mobile = normalize_phone(raw)
            if mobile:
                mobile_to_name[mobile] = name
                all_numbers.add(mobile)

    # Debug: log matched numbers
    if not all_numbers:
        return Response({
            "status": False,
            "message": "No valid phone numbers extracted",
            "debug": f"canonical_contacts={canonical_contacts}"
        })

    # -------- MATCH WITH VOTERLIST --------
    voters = (
        VoterList.objects
        .filter(
            Q(mobile_no__in=all_numbers) |
            Q(alternate_mobile1__in=all_numbers) |
            Q(alternate_mobile2__in=all_numbers)
        )
        .values(
            "voter_list_id",
            "mobile_no",
            "alternate_mobile1",
            "alternate_mobile2",
            "voter_name_eng",
            "voter_name_marathi"
        )
    )

    matched = []
    to_create = []
    
    for v in voters:
        voter_name = v.get("voter_name_eng") or v.get("voter_name_marathi") or "Unknown"
        # create one match per phone-field that appears in the incoming contacts
        for fld in ("mobile_no", "alternate_mobile1", "alternate_mobile2"):
            val = v.get(fld)
            if not val:
                continue
            if val not in all_numbers:
                continue

            contact_name = mobile_to_name.get(val)

            matched.append({
                "mobile_no": val,
                "contact_name": contact_name,
                "voter_id": v["voter_list_id"],
                "voter_name": voter_name
            })

            to_create.append(
                UserVoterContact(
                    user_id=user_id,
                    voter_id=v["voter_list_id"],
                    contact_name=contact_name,
                    voter_name=voter_name,
                    mobile_no=val
                )
            )
    
    #  Bulk insert (single query)
    if to_create:
        UserVoterContact.objects.bulk_create(
            to_create,
            ignore_conflicts=True,
            batch_size=1000   # IMPORTANT for performance
        )
    
    return Response({
        "status": True,
        "count": len(matched),
        "matched": matched
    })