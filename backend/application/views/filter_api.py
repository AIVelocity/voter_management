from ..models import VoterList,VoterUserMaster
from django.db.models import Q
from rest_framework_simplejwt.tokens import AccessToken
from django.core.paginator import Paginator
from .voters_info_api import format_mobile_with_country_code, split_marathi_name
import re
from collections import Counter

def apply_dynamic_initial_search(qs, search):

    tokens = [t.strip().lower() for t in search.split() if t.strip()]
    token_counts = Counter(tokens)

    # --------- DB side presence filter ---------
    for token in token_counts:
        qs = qs.filter(
            Q(voter_name_eng__iregex=rf'\m{token}') |
            Q(voter_id__icontains=token)
        )

    # --------- Python side frequency validation ---------
    final_results = []
    words_re = re.compile(r"[A-Za-z]+")

    for v in qs:
        words = words_re.findall((v.voter_name_eng or "").lower())
        voter_id = (v.voter_id or "").lower()

        counts = Counter()
        for t in token_counts:
            for w in words:
                if w.startswith(t):
                    counts[t] += 1

        valid = True
        for t, required in token_counts.items():
            # If token matched voter_id, accept it without name matching
            if t in voter_id:
                continue

            if counts[t] < required:
                valid = False
                break

        if valid:
            final_results.append(v)

    return final_results


def apply_multi_filter(qs, field, value):
    if not value:
        return qs

    values = [v.strip() for v in value.split(",") if v.strip()]

    if "null" in [v.lower() for v in values]:
        return qs.filter(**{f"{field}__isnull": True})

    return qs.filter(**{f"{field}__in": values})

def apply_tag_filter(qs, tag_value):
    if not tag_value:
        return qs

    TAG_NAME_TO_ID = {
        "green": 1,
        "orange": 2,
        "red": 3,
        "golden": 4,
        "white": 5,
    }

    tag_names = [t.strip().lower() for t in tag_value.split(",")]
    tag_ids = [TAG_NAME_TO_ID[t] for t in tag_names if t in TAG_NAME_TO_ID]

    return qs.filter(tag_id__in=tag_ids) if tag_ids else qs


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def filter(request):
    lang = request.headers.get("Accept-Language", "en")
    is_marathi = lang.lower().startswith("mr")
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))
    sort = request.GET.get("sort")
    search = request.GET.get("search")

    first_name = request.GET.get("first_name")
    middle_name = request.GET.get("middle_name")
    last_name = request.GET.get("last_name")

    age_max = request.GET.get("age_max")
    age_min = request.GET.get("age_min")

    location = request.GET.get("location")
    tag = request.GET.get("tag_id")
    gender = request.GET.get("gender")
    first_ends = request.GET.get("first_ends")
    middle_ends = request.GET.get("middle_ends")
    last_ends = request.GET.get("last_ends")
    
    kramank = request.GET.get("kramank")
    voter_id = request.GET.get("voter_id")
    
    religion = request.GET.get("religion")
    age_ranges = request.GET.get("age_ranges")
    # caste = request.GET.get("caste")

    # badge = request.GET.get("badge")

    user_id = None
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = AccessToken(auth_header.split(" ")[1])
            user_id = token["user_id"]
        except Exception:
            pass

    if not user_id:
        return Response(
            {"status": False, "message": "Unauthorized"},
            status=401
        )

    # -------- USER & ROLE --------
    try:
        user = (
            VoterUserMaster.objects
            .select_related("role")
            .get(user_id=user_id)
        )
    except VoterUserMaster.DoesNotExist:
        return Response(
            {"status": False, "message": "User not found"},
            status=404
        )

    from django.db.models import Q
    
    privileged_roles = ["Volunteer"]
    
    if user.role.role_name in privileged_roles:
        # Check if user has any assigned voters
        has_assigned_voters = VoterList.objects.filter(user_id=user_id).exists()
    
        if has_assigned_voters:
            qs = (
                VoterList.objects
                .select_related("tag_id")
                .filter(user_id=user_id)
                .order_by("sr_no")
            )
        else:
            qs = (
                VoterList.objects
                .select_related("tag_id")
                .order_by("sr_no")
            )
    else:
        qs = (
            VoterList.objects
            .select_related("tag_id")
            .order_by("sr_no")
        )
    
    # Apply advanced search (name + voter_id)
    if search:
        qs = apply_dynamic_initial_search(qs, search)

    if voter_id:
        qs = qs.filter(voter_id__icontains=voter_id)
    
    if kramank:
        qs = qs.filter(kramank__icontains=kramank)
        
    # Field filters
    if first_name:
        # qs = qs.filter(first_name__icontains=first_name)
        qs = qs.filter(first_name__istartswith=first_name)
        

    if middle_name:
        # qs = qs.filter(middle_name__icontains=middle_name)
        qs = qs.filter(middle_name__istartswith=middle_name)
        

    if last_name:
        # qs = qs.filter(last_name__icontains=last_name)
        qs = qs.filter(last_name__istartswith=last_name)


    from django.db.models import Q

    if age_ranges:
        age_q = Q()
        ranges = age_ranges.split(",")

        for r in ranges:
            try:
                min_age, max_age = r.split("-")
                age_q |= Q(
                    age_eng__gte=int(min_age.strip()),
                    age_eng__lte=int(max_age.strip())
                )
            except ValueError:
                continue  # skip invalid ranges

        qs = qs.filter(age_q)

    if location:
        qs = qs.filter(location__icontains=location)
     
    
    if sort:
        qs = qs.order_by(sort)

    # Apply ENDS WITH filters
    if first_ends:
        qs = qs.filter(first_name__iendswith=first_ends)
    
    if middle_ends:
        qs = qs.filter(middle_name__iendswith=middle_ends)
    
    if last_ends:
        qs = qs.filter(last_name__iendswith=last_ends)
        
    qs = apply_multi_filter(qs, "cast", request.GET.get("caste"))
    qs = apply_multi_filter(qs, "religion_id", request.GET.get("religion"))
    qs = apply_multi_filter(qs, "occupation", request.GET.get("occupation"))
    qs = apply_multi_filter(qs, "gender_eng", request.GET.get("gender"))
    qs = apply_tag_filter(qs, request.GET.get("tag_id"))
    
    # Pagination
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = []
    for v in page_obj:
        if is_marathi:
            first_name, middle_name, last_name = split_marathi_name(
                v.voter_name_marathi
            )

            voter_name_eng = v.voter_name_marathi
            age_eng = v.age
            gender_eng = v.gender
        else:
            first_name = v.first_name
            middle_name = v.middle_name
            last_name = v.last_name

            voter_name_eng = v.voter_name_eng
            age_eng = v.age_eng
            gender_eng = v.gender_eng
        
        has_whatsapp = any([
        bool(v.mobile_no),
        bool(v.alternate_mobile1),
        bool(v.alternate_mobile2),
    ])
        data.append({
            "sr_no" : v.sr_no,
            "voter_list_id": v.voter_list_id,
            "voter_name_eng": voter_name_eng,
            "voter_id": v.voter_id,
            "gender": gender_eng,
            "location": v.location,
            "badge": v.badge,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "kramank": v.kramank,
            "age":age_eng,
            "ward_id": v.ward_no,
            "show_whatsapp": has_whatsapp,
            "mobile_no": format_mobile_with_country_code(
                v.mobile_no or v.alternate_mobile1 or v.alternate_mobile2 or None
            ),
        })

    return Response({
        "status": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })
    
    