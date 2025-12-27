from .filter_api import apply_multi_filter, apply_tag_filter
from .filter_api import apply_dynamic_initial_search
from ..models import VoterList, VoterRelationshipDetails, ActivityLog, UserContactPayload, UserVoterContact
from deep_translator import GoogleTranslator
from .contact_match_api import canonicalize_contacts, normalize_phone
from django.db.models import Q
import re
from collections import Counter
from django.conf import settings
import os
import csv
import json

def build_voter_queryset(request, user):
    qs = VoterList.objects.select_related("tag_id")

    # ---- ROLE BASED ----
    if user.role.role_name not in ["SuperAdmin", "Admin"]:
        qs = qs.filter(user_id=user.user_id)

    # ---- SEARCH ----
    search = request.GET.get("search")
    if search:
        qs = apply_dynamic_initial_search(qs, search)

    # ---- SIMPLE FILTERS ----
    if request.GET.get("voter_id"):
        qs = qs.filter(voter_id__icontains=request.GET["voter_id"])

    if request.GET.get("kramank"):
        qs = qs.filter(kramank__icontains=request.GET["kramank"])

    # ---- NAME FILTERS ----
    if request.GET.get("first_name"):
        qs = qs.filter(first_name__istartswith=request.GET["first_name"])

    if request.GET.get("middle_name"):
        qs = qs.filter(middle_name__istartswith=request.GET["middle_name"])

    if request.GET.get("last_name"):
        qs = qs.filter(last_name__istartswith=request.GET["last_name"])

    # ---- AGE RANGES ----
    age_ranges = request.GET.get("age_ranges")
    if age_ranges:
        age_q = Q()
        for r in age_ranges.split(","):
            try:
                lo, hi = r.split("-")
                age_q |= Q(age_eng__gte=int(lo), age_eng__lte=int(hi))
            except ValueError:
                pass
        qs = qs.filter(age_q)

    # ---- MULTI FILTERS ----
    qs = apply_multi_filter(qs, "cast", request.GET.get("caste"))
    qs = apply_multi_filter(qs, "religion_id", request.GET.get("religion"))
    qs = apply_multi_filter(qs, "occupation", request.GET.get("occupation"))
    qs = apply_multi_filter(qs, "gender_eng", request.GET.get("gender"))
    qs = apply_tag_filter(qs, request.GET.get("tag_id"))

    # ---- LOCATION ----
    if request.GET.get("location"):
        qs = qs.filter(location__icontains=request.GET["location"])

    # ---- SORT ----
    if request.GET.get("sort"):
        qs = qs.order_by(request.GET["sort"])
    else:
        qs = qs.order_by("sr_no")

    return qs

class Translator:
    def __init__(self, source="auto"):
        self.source = source

    def translate(self, text, target_lang):
        return GoogleTranslator(
            source=self.source,
            target=target_lang
        ).translate(text)
        
def log_user_update(
    *,
    user,
    action,
    description,
    voter_list_id=None,
    old_data=None,
    new_data=None,
    ip=None,
    changed_fields=None
):
    """
    old_data / new_data:
    {
        "mobile_no": "1111111111",
        "address_line1": "Old Address"
    }
    """
    if changed_fields:
        old_data = {k: v["old"] for k, v in changed_fields.items()}
        new_data = {k: v["new"] for k, v in changed_fields.items()}
    log_entry = ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        old_data=old_data,
        new_data=new_data,
        ip_address=ip,
        voter_id=voter_list_id
    )
    logs_dir = os.path.join(settings.BASE_DIR, "local_logs")
    os.makedirs(logs_dir, exist_ok=True)

    csv_path = os.path.join(logs_dir, "activity_logs.csv")

    file_exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header only once:
        if not file_exists:
            writer.writerow([
                "log_id",
                "user_id",
                "action",
                "description",
                "ip_address",
                "voter_id",
                "old_data",
                "new_data",
                "created_at"
            ])

        # Append a new row:
        writer.writerow([
            log_entry.log_id,
            log_entry.user.user_id if log_entry.user else None,
            log_entry.action,
            log_entry.description,
            log_entry.ip_address,
            voter_list_id,
            json.dumps(old_data, ensure_ascii=False),
            json.dumps(new_data, ensure_ascii=False),
            str(log_entry.created_at),
        ])
    return log_entry


def save_relation(voter, relation, related_voter_id):
    """
    Persists a voter relationship safely.
    Prevents duplicates automatically using DB unique constraint.
    """

    if not voter or not related_voter_id:
        return

    VoterRelationshipDetails.objects.get_or_create(
        voter=voter,
        related_voter_id=related_voter_id,
        relation_with_voter=relation.lower(),
    )
    
def build_member(p, is_marathi):
    if is_marathi and p.voter_name_marathi:
        return {
            "name": p.voter_name_marathi,
            "voter_list_id": p.voter_list_id,
        }

    # fallback to English
    return {
        "name": p.voter_name_eng,
        "voter_list_id": p.voter_list_id,
    }
def get_family_from_db(voter, is_marathi=False):

    relations = (
        VoterRelationshipDetails.objects
        .filter(voter=voter)
        .select_related("related_voter")
    )

    siblings = []
    children = []

    father = mother = spouse = wife = husband = None

    for rel in relations:
        p = rel.related_voter
        member = build_member(p, is_marathi)

        rel_type = rel.relation_with_voter

        if rel_type == "father":
            father = member

        elif rel_type == "mother":
            mother = member

        elif rel_type == "spouse":
            spouse = member

        elif rel_type == "wife":
            wife = member

        elif rel_type == "husband":
            husband = member

        elif rel_type == "child":
            children.append(member)

        elif rel_type == "sibling":
            siblings.append(member)

    return {
        "father": father,
        "mother": mother,
        "wife": wife,
        "husband": husband,
        "spouse": spouse,
        "siblings": siblings,
        "children": children,
    }

def rematch_contacts_for_voter(voter, user):
    
    print("VOTER.USER =", voter.user)
    print("PAYLOAD COUNT =", UserContactPayload.objects.filter(user=voter.user).count())

    numbers = {
        voter.mobile_no,
        voter.alternate_mobile1,
        voter.alternate_mobile2
    }
    numbers = {n for n in numbers if n}

    if not numbers:
        return

    payloads = (
        UserContactPayload.objects
        .filter(user=user)
        .order_by("-created_at")[:5]   # last N payloads only
    )

    print("VOTER.USER =", user)
    print("PAYLOAD COUNT =", UserContactPayload.objects.filter(user=user).count())
    to_create = []

    for p in payloads:
        contacts = canonicalize_contacts(p.payload)

        for contact in contacts:
            for raw in contact["numbers"]:
                mobile = normalize_phone(raw)
                if mobile in numbers:
                    to_create.append(
                        UserVoterContact(
                            user=user,
                            voter=voter,
                            contact_name=contact["name"],
                            voter_name=voter.voter_name_eng or voter.voter_name_marathi,
                            mobile_no=mobile
                        )
                    )

    if to_create:
        UserVoterContact.objects.bulk_create(
            to_create,
            ignore_conflicts=True,
            batch_size=500
        )
