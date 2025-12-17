from django.http import JsonResponse
from ..models import VoterList,VoterTag,ActivityLog,VoterUserMaster,Caste,Religion,Occupation
from .view_utils import save_relation,get_family_from_db
from rest_framework_simplejwt.tokens import AccessToken
from django.db.models import Q
from django.utils import timezone
import pytz


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
def single_voters_info(request, voter_list_id):

    if request.method != "GET":
        return JsonResponse({
            "status": False,
            "message": "GET method required"
        }, status=405)

    # ---------- FETCH VOTER ----------
    try:
        voter = (
            VoterList.objects
            .select_related("tag_id", "occupation", "cast", "religion")
            .get(voter_list_id=voter_list_id)
        )
    except VoterList.DoesNotExist:
        return JsonResponse({
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

    age = safe_age(voter.age_eng)

    # ---------- FAMILY FROM DB (SOURCE OF TRUTH) ----------
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

    # ---------- FINAL RESPONSE ----------
    data = {
        "voter_list_id": voter.voter_list_id,
        "voter_name_eng": voter.voter_name_eng,
        "sr_no": voter.sr_no,
        "voter_id": voter.voter_id,

        "first_name": voter.first_name,
        "middle_name": voter.middle_name,
        "last_name": voter.last_name,

        "address": voter.current_address,
        "mobile_no": voter.mobile_no,
        "alternate_mobile_no1": voter.alternate_mobile1,
        "alternate_mobile_no2": voter.alternate_mobile2,
        "kramank": voter.kramank,
        "full_address":voter.address_line1,
        "age": age,
        "gender": voter.gender_eng,
        "ward_id": voter.ward_no,

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
        

        # AUDIT
        "tag_last_updated_by": tag_last_updated_by,
        "tag_last_updated_at": tag_last_updated_at,
        "comment_last_updated_by": comment_last_updated_by,
        "comment_last_updated_at": comment_last_updated_at,

        "check_progress": voter.check_progress
    }

    return JsonResponse({
        "status": True,
        "data": data
    })
