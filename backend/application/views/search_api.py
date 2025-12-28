from ..models import VoterList,VoterTag
from .voters_info_api import format_mobile_with_country_code, split_marathi_name
import re
from collections import Counter
from django.db.models import Q
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .filter_api import apply_dynamic_initial_search


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def voters_search(request):
    lang = request.headers.get("Accept-Language", "en")
    is_marathi = lang.lower() in ["mr", "mr-in", "marathi"]

    search = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))

    user = request.user
    user_id = user.user_id
    role = user.role.role_name

    privileged_roles = ["Volunteer"]

    base_qs = VoterList.objects.select_related("tag_id")

    # ---------- ASSIGNMENT LOGIC ----------
    if role in privileged_roles:
        has_assigned = base_qs.filter(user_id=user_id).exists()

        if has_assigned:
            qs = base_qs.filter(user_id=user_id)
        else:
            qs = base_qs.all()
    else:
        qs = base_qs.all()

    # ---------- SEARCH ----------
    if search:
        qs = apply_dynamic_initial_search(qs, search)

    # ---------- PAGINATION ----------
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = []

    for v in page_obj:
        if is_marathi:
            first_name, middle_name, last_name = split_marathi_name(
                v.voter_name_marathi
            )
            voter_name = v.voter_name_marathi
            age = v.age
            gender = v.gender
        else:
            first_name = v.first_name
            middle_name = v.middle_name
            last_name = v.last_name
            voter_name = v.voter_name_eng
            age = v.age_eng
            gender = v.gender_eng

        has_whatsapp = any([
            bool(v.mobile_no),
            bool(v.alternate_mobile1),
            bool(v.alternate_mobile2),
        ])

        data.append({
            "sr_no": v.sr_no,
            "voter_list_id": v.voter_list_id,
            "voter_id": v.voter_id,
            "first_name": first_name,
            "last_name": last_name,
            "voter_name_eng": voter_name,
            "kramank": v.kramank,
            "age": age,
            "gender": gender,
            "ward_id": v.ward_no,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "badge": v.badge,
            "location": v.location,
            "show_whatsapp": has_whatsapp,
            "mobile_no": format_mobile_with_country_code(
                v.mobile_no or v.alternate_mobile1 or v.alternate_mobile2
            ),
        })

    return Response({
        "status": True,
        "query": search,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data,
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated]) 
def family_dropdown_search(request):
    search = request.GET.get("search", "").strip()
    # print(search)
    
    lang = request.headers.get("Accept-Language", "en")
    is_marathi = lang in ["mr", "mr-in", "marathi"]
    
    exclude_id = request.GET.get("exclude_id")   
    # print(exclude_id)
    page = int(request.GET.get("page", 1))
    size = 30   

    qs = VoterList.objects.all()

    # Exclude the current voter (self cannot be father/mother)
    if exclude_id:
        qs = qs.exclude(voter_list_id=exclude_id)

    if search:
        qs = apply_dynamic_initial_search(qs, search)

    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data=[]
    for v in page_obj:
        if is_marathi:
            first_name, middle_name, last_name = split_marathi_name(
                v.voter_name_marathi
            )

            voter_name_eng = v.voter_name_marathi
            age_eng = v.age
            gender_eng = v.gender
            tag = v.tag_id.tag_name_mar if v.tag_id else None
        else:
            first_name = v.first_name
            middle_name = v.middle_name
            last_name = v.last_name

            voter_name_eng = v.voter_name_eng
            age_eng = v.age_eng
            gender_eng = v.gender_eng
            tag = v.tag_id.tag_name if v.tag_id else None
            
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
            "tag": tag,
            "badge": v.badge,
            "location": v.location,
            "show_whatsapp": has_whatsapp,
            "mobile_no": format_mobile_with_country_code(
                v.mobile_no or v.alternate_mobile1 or v.alternate_mobile2 or None
            ),
        })
    return Response({
        "status": True,
        "query": search,
        "exclude_id": exclude_id,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "results": data
    })

  