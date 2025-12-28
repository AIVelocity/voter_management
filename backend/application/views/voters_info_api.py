from ..models import VoterList,VoterUserMaster
from django.core.cache import cache
from django.core.paginator import Paginator
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

def split_marathi_name(full_name):
    if not full_name:
        return None, None, None

    parts = full_name.strip().split()

    last_name = parts[0] if len(parts) > 0 else None
    first_name = parts[1] if len(parts) > 1 else None
    middle_name = " ".join(parts[2:]) if len(parts) > 2 else None

    return first_name, middle_name, last_name

def format_mobile_with_country_code(mobile: str) -> str:
    """Prepend 91 to 10-digit mobile numbers."""
    if not mobile:
        return None
    mobile = mobile.strip()
    if len(mobile) == 10:
        return f"91{mobile}"
    return mobile


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def voters_info(request):
    lang = request.headers.get("Accept-Language", "en")
    # print(lang)
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))
    is_marathi = lang in ["mr", "mr-in", "marathi"]
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
    

    # -------- GET USER & ROLE --------
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

    # -------- ROLE-BASED QUERY --------
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
            "voter_id": v.voter_id,
            "first_name": first_name,
            "last_name": last_name,
            # "voter_name_marathi": translator.translate(v.voter_name_marathi, lang),
            "voter_name_eng": voter_name_eng,
            "kramank": v.kramank,
            "age": age_eng,
            "gender": gender_eng,
            "ward_id": v.ward_no,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "badge": v.badge,
            "location": v.location,
            "show_whatsapp": has_whatsapp,
            "mobile_no": format_mobile_with_country_code(
                v.mobile_no or v.alternate_mobile1 or v.alternate_mobile2 or None
            ),
        })

    response_data = {
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    }

    # 🔹 Save to Redis (10 minutes)
    # cache.set(cache_key, response_data, timeout=600)

    return Response({
        "status": True,
        "source": "db",
        **response_data
    })
    # return Response({
    #     "status": True,
    #     "page": page,
    #     "page_size": size,
    #     "total_pages": paginator.num_pages,
    #     "total_records": paginator.count,
    #     "records_returned": len(data),
    #     "data": data
    # })