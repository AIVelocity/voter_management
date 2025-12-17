from django.http import JsonResponse
from ..models import VoterList,VoterUserMaster
from django.core.cache import cache
from django.core.paginator import Paginator
from rest_framework_simplejwt.tokens import AccessToken


def voters_info(request):

    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))

    user_id = None
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = AccessToken(auth_header.split(" ")[1])
            user_id = token["user_id"]
        except Exception:
            pass

    if not user_id:
        return JsonResponse(
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
        return JsonResponse(
            {"status": False, "message": "User not found"},
            status=404
        )

    # -------- ROLE-BASED QUERY --------
    if user.role.role_name == "SuperAdmin":
        qs = (
            VoterList.objects
            .select_related("tag_id")
            .order_by("ward_no", "voter_list_id")
        )
    else:
        qs = (
            VoterList.objects
            .select_related("tag_id")
            .filter(user_id=user_id)
            .order_by("ward_no", "voter_list_id")
        )

    # cache_key = f"voters:page:{page}:size{size}"

    # cache_response = cache.get(cache_key)
    
    # if cache_response:
    #     return JsonResponse({
    #         "status" : True,
    #         "source":"cache",
    #         **cache_response
    #     })
        
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = []

    for v in page_obj:
        data.append({
            "sr_no" : v.serial_number,
            "voter_list_id": v.voter_list_id,
            "voter_id": v.voter_id,
            "first_name":v.first_name,
            "last_name" : v.last_name,
            "voter_name_marathi": v.voter_name_marathi,
            "voter_name_eng": v.voter_name_eng,
            "kramank": v.kramank,
            "age": v.age_eng,
            "gender": v.gender_eng,
            "ward_id": v.ward_no,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "badge": v.badge,
            "location": v.location
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

    return JsonResponse({
        "status": True,
        "source": "db",
        **response_data
    })
    # return JsonResponse({
    #     "status": True,
    #     "page": page,
    #     "page_size": size,
    #     "total_pages": paginator.num_pages,
    #     "total_records": paginator.count,
    #     "records_returned": len(data),
    #     "data": data
    # })