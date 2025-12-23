from ..models import VoterList,ActivityLog,VoterUserMaster
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .view_utils import get_family_from_db, save_relation
from rest_framework_simplejwt.tokens import AccessToken
from django.db.models import Q
from django.utils import timezone
import pytz
from django.utils.translation import gettext as _
from .voters_info_api import split_marathi_name

ist = pytz.timezone("Asia/Kolkata")

def make_aware_if_needed(dt):
    if dt is None:
        return None

    # If already aware → return as-is
    if timezone.is_aware(dt):
        return dt

    # Make it aware in UTC
    return timezone.make_aware(dt, timezone=pytz.UTC)

def format_indian_datetime(dt):
    if not dt:
        return None
    ist = pytz.timezone("Asia/Kolkata")

    # First make dt timezone aware in UTC
    dt = make_aware_if_needed(dt)

    dt_ist = dt.astimezone(ist)
    return dt_ist.strftime("%d-%m-%Y %I:%M %p")

# ---------------------------------------------
# SINGLE VOTER INFO
# ---------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def single_voters_info(request, voter_list_id):

    if request.method != "GET":
        return Response({
            "status": False,
            "message":  _("GET method required")
        }, status=405)

    # ---------- FETCH VOTER ----------
    try:
        lang = request.headers.get("Accept-Language", "en")
        print(lang)
        is_marathi = lang in ["mr", "mr-in", "marathi"]
        voter = (
            VoterList.objects
            .select_related("tag_id", "occupation", "cast", "religion")
            .get(voter_list_id=voter_list_id)
        )
    except VoterList.DoesNotExist:
        return Response({
            "status": False,
            "message": "Voter not found"
        }, status=404)

    # ---------- AUTH USER ----------
    user = None
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = AccessToken(auth_header.split(" ")[1])
            user = VoterUserMaster.objects.filter(
                user_id=token.get("user_id")
            ).select_related("role").first()
    except Exception:
        pass

    # ---------- HELPERS ----------
    def safe_age(v):
        try:
            return int(str(v).strip())
        except:
            return None
    def parse_kramank(value):
        try:
            return int(str(value).split("/")[-1])
        except:
            return 0
        
    kramank = parse_kramank(voter.kramank)
    age = safe_age(voter.age_eng)
    
    def calculate_and_save_family(voter):
        is_male = voter.gender_eng.lower() == "male"

        father = father_name = father_id = None
        mother = mother_name = mother_id = None
        wife = wife_name = wife_id = None
        husband = husband_name = husband_id = None

        siblings = []
        children = []
        other_relatives = []
        BloodRelatedFam = []

        # -------- YOUR EXISTING LOGIC -----------
        # (No behavioural change)

        # --- MALE ---
        if is_male:
            father = VoterList.objects.filter(
                first_name=voter.middle_name,
                last_name=voter.last_name,
                gender_eng__iexact="male"
            ).first()

            if father:
                father_name = f"{father.first_name} {father.middle_name} {father.last_name}"
                father_id = father.voter_list_id
            else:
                father_name = " ".join(filter(None, [
                    voter.middle_name,
                    voter.last_name
                ]))

        # --- FEMALE ---
        else:
            male_match = VoterList.objects.filter(
                first_name=voter.middle_name,
                last_name=voter.last_name,
                gender_eng__iexact="male"
            ).first()

            voter_age = safe_age(voter.age_eng)
            male_age = safe_age(male_match.age_eng) if male_match else None

            if male_match and voter_age and male_age:
                age_gap = male_age - voter_age

                if age_gap >= 18:
                    father = male_match
                    father_name = f"{father.first_name} {father.middle_name} {father.last_name}"
                    father_id = father.voter_list_id
                else:
                    husband = male_match
                    husband_name = f"{husband.first_name} {husband.middle_name} {husband.last_name}"
                    husband_id = husband.voter_list_id

        # --- MOTHER ---
        if father:
            mother = VoterList.objects.filter(
                middle_name=father.first_name,
                last_name=father.last_name,
                gender_eng__iexact="female"
            ).first()

            if mother:
                mother_name = f"{mother.first_name} {mother.middle_name} {mother.last_name}"
                mother_id = mother.voter_list_id

        # ---- SIBLINGS ----

        father_first_name_for_siblings = (
            father.first_name if is_male and father else voter.middle_name
        )

        if father_first_name_for_siblings and age and kramank:
            family_members = VoterList.objects.filter(
                last_name=voter.last_name
            ).exclude(voter_list_id=voter.voter_list_id)

            for p in family_members:
                p_age = safe_age(p.age_eng)
                p_kramank = parse_kramank(p.kramank)

                if (
                    p.middle_name == father_first_name_for_siblings and
                    p_age is not None and
                    age is not None and
                    abs(p_age - age) <= 18 and
                    p_kramank and
                    abs(p_kramank - kramank) <= 5
                ):
                    siblings.append({
                        "name": f"{p.first_name} {p.middle_name} {p.last_name}",
                        "voter_list_id": p.voter_list_id
                    })

        # ---- WIFE ----
        if is_male:
            wife = VoterList.objects.filter(
                middle_name=voter.first_name,
                last_name=voter.last_name,
                gender_eng__iexact="female"
            ).first()

            if wife:
                wife_name = f"{wife.first_name} {wife.middle_name} {wife.last_name}"
                wife_id = wife.voter_list_id

        # ---- CHILDREN ----

        parent_firstname_for_child = (
            voter.first_name if is_male
            else husband.first_name if husband
            else None
        )

        if parent_firstname_for_child and age and kramank:
            kids = VoterList.objects.filter(
                middle_name=parent_firstname_for_child,
                last_name=voter.last_name
            ).exclude(voter_list_id=voter.voter_list_id)

            for kid in kids:
                kid_age = safe_age(kid.age_eng)
                kid_kramank = parse_kramank(kid.kramank)

                if kid_age and age - kid_age >= 15 and abs(kid_kramank - kramank) <= 5:
                    children.append({
                        "name": f"{kid.first_name} {kid.middle_name} {kid.last_name}",
                        "voter_list_id": kid.voter_list_id
                    })

        # ---- REMOVE SIBLINGS DUPED AS CHILDREN ----

        child_ids = {c["voter_list_id"] for c in children}
        siblings = [s for s in siblings if s["voter_list_id"] not in child_ids]

        # ---- SAVE RELATIONSHIPS ----

        save_relation(voter, "father", father_id)
        save_relation(voter, "mother", mother_id)
        # save_relation(voter, "husband", husband_id)
        # save_relation(voter, "wife", wife_id)
        spouse_id = wife_id if wife_id else husband_id
        save_relation(voter, "spouse", spouse_id)


        for c in children:
            save_relation(voter, "child", c["voter_list_id"])

        for s in siblings:
            save_relation(voter, "sibling", s["voter_list_id"])

        # ---- BUILD RESPONSE OBJECT ----

        BloodRelatedFam.extend(
            [
                {"relation": "Father",  "name": father_name,  "voter_list_id": father_id},
                {"relation": "Mother",  "name": mother_name,  "voter_list_id": mother_id},
                {"relation": "Wife",    "name": wife_name,    "voter_list_id": wife_id},
                {"relation": "Husband","name": husband_name, "voter_list_id": husband_id},
            ]
        )

        BloodRelatedFam += [
            {"relation": "Child","name": c["name"],"voter_list_id": c["voter_list_id"]}
            for c in children
        ]

        BloodRelatedFam += [
            {"relation": "Sibling","name": s["name"],"voter_list_id": s["voter_list_id"]}
            for s in siblings
        ]

        return {
            "father_name": father_name,
            "mother_name": mother_name,
            "wife_name": wife_name,
            "husband_name": husband_name,
            "siblings": siblings,
            "children": children,
            "BloodRelatedFam": BloodRelatedFam
        }

    # ---------- FAMILY FROM DB (SOURCE OF TRUTH) ----------
    family = get_family_from_db(voter, is_marathi)
    
    if not (
        family["father"] or family["mother"] or family["wife"]
        or family["husband"] or family["siblings"] or family["children"]
    ):
        calculate_and_save_family(voter)
        family = get_family_from_db(voter)

    father = family.get("father")
    mother = family.get("mother")
    spouse = family.get("spouse")   # DIRECT FROM DB
    siblings = family.get("siblings", [])
    children = family.get("children", [])

    # ---------- BUILD BLOOD RELATED FAMILY ----------
    BloodRelatedFam = []

    if father:
        BloodRelatedFam.append({
            "relation": "Father",
            **father
        })

    if mother:
        BloodRelatedFam.append({
            "relation": "Mother",
            **mother
        })

    if spouse:
        BloodRelatedFam.append({
            "relation": "Spouse",
            **spouse
        })

    for s in siblings:
        BloodRelatedFam.append({
            "relation": "Sibling",
            **s
        })

    for c in children:
        BloodRelatedFam.append({
            "relation": "Child",
            **c
        })

    # ---------- ACTIVITY LOGS ----------
    tag_log = (
        ActivityLog.objects
        .filter(
            voter_id=voter_list_id
        )
        .filter(Q(old_data__has_key="tag_id") | Q(new_data__has_key="tag_id"))
        .select_related("user")
        .order_by("-created_at")
        .first()
    )

    comment_log = (
        ActivityLog.objects
        .filter(
            voter_id=voter_list_id
        )
        .filter(Q(old_data__has_key="comments") | Q(new_data__has_key="comments"))
        .select_related("user")
        .order_by("-created_at")
        .first()
    )

    tag_last_updated_by = "NA"
    tag_last_updated_at = None
    comment_last_updated_by = "NA"
    comment_last_updated_at = None

    if user and user.role and user.role.role_name == "SuperAdmin":

        if tag_log and tag_log.user:
            tag_last_updated_by = f"{tag_log.user.last_name} {tag_log.user.first_name}".strip()
            tag_last_updated_at = tag_log.created_at

        if comment_log and comment_log.user:
            comment_last_updated_by = f"{comment_log.user.last_name} {comment_log.user.first_name}".strip()
            comment_last_updated_at = comment_log.created_at

    tag_last_updated_at = format_indian_datetime(
        make_aware_if_needed(tag_last_updated_at)
    )
    comment_last_updated_at = format_indian_datetime(
        make_aware_if_needed(comment_last_updated_at)
    )
    
    if is_marathi:
        first_name, middle_name, last_name = split_marathi_name(
            voter.voter_name_marathi
        )
        voter_name_eng = voter.voter_name_marathi
        age_eng = age
        gender_eng = voter.gender
    else:
        first_name = voter.first_name
        middle_name = voter.middle_name
        last_name = voter.last_name
        voter_name_eng = voter.voter_name_eng
        age_eng = age
        gender_eng = voter.gender_eng
    # ---------- FINAL RESPONSE ----------
    data = {
        "voter_list_id": voter.voter_list_id,
        "voter_name_eng": voter_name_eng,
        "sr_no": voter.sr_no,
        "voter_id": voter.voter_id,

        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,

        "address": voter.current_address,
        "mobile_no": voter.mobile_no,
        "alternate_mobile_no1": voter.alternate_mobile1,
        "alternate_mobile_no2": voter.alternate_mobile2,
        "kramank": voter.kramank,
        "full_address":voter.address_line1,
        "age": age_eng,
        "gender": gender_eng,
        "ward_id": voter.ward_no,
        "location": voter.location,
        "badge": voter.badge,
        "tag": voter.tag_id.tag_name if voter.tag_id else None,
        "tag_obj": {
            "id": voter.tag_id.tag_id if voter.tag_id else None,
            "name": voter.tag_id.tag_name if voter.tag_id else None
        },

        "occupation_obj": {
            "id": voter.occupation_id,
            "name": voter.occupation.occupation_name if voter.occupation else None
        },

        "caste_obj": {
            "id": voter.cast_id,
            "name": voter.cast.caste_name if voter.cast else None
        },

        "religion_obj": {
            "id": voter.religion_id,
            "name": voter.religion.religion_name if voter.religion else None
        },

        # FAMILY
        "father": father,
        "mother": mother,
        "spouse": spouse,      # ALWAYS PRESENT
        "siblings": siblings,
        "children": children,
        "BloodRelatedFam": BloodRelatedFam,
        "comments":voter.comments,
        

        # AUDIT
        "tag_last_updated_by": tag_last_updated_by,
        "tag_last_updated_at": tag_last_updated_at,
        "comment_last_updated_by": comment_last_updated_by,
        "comment_last_updated_at": comment_last_updated_at,

        "check_progress": voter.check_progress
    }

    return Response({
        "status": True,
        "data": data
    })
