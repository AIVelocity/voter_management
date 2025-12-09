from ..models import VoterList
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse


def filter(request):

    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 50))
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

    # STARTS WITH filters
    first_starts = request.GET.get("first_starts")
    middle_starts = request.GET.get("middle_starts")
    last_starts = request.GET.get("last_starts")

    # ENDS WITH filters
    first_ends = request.GET.get("first_ends")
    middle_ends = request.GET.get("middle_ends")
    last_ends = request.GET.get("last_ends")
    
    kramank = request.GET.get("kramank")
    badge = request.GET.get("badge")

    qs = VoterList.objects.select_related("tag_id").all()

    # Global search
    if search:
        tokens = search.lower().split()
        search_q = Q()
        for t in tokens:
            search_q &= (
                Q(first_name__icontains=t) |
                Q(middle_name__icontains=t) |
                Q(last_name__icontains=t)
            )
        qs = qs.filter(search_q)

    if badge:
        qs = qs.filter(badge__icontains=badge)
        
    if kramank:
        qs = qs.filter(kramank__icontains=kramank)
        
    # Field filters
    if first_name:
        qs = qs.filter(first_name__icontains=first_name)

    if middle_name:
        qs = qs.filter(middle_name__icontains=middle_name)

    if last_name:
        qs = qs.filter(last_name__icontains=last_name)

    if age_max:
        qs = qs.filter(age_eng__lte=age_max)

    if age_min:
        qs = qs.filter(age_eng__gte=age_min)

    if location:
        qs = qs.filter(location__icontains=location)

    if tag:
        qs = qs.filter(tag_id__id=tag)
    
    if sort:
        qs = qs.order_by(sort)

    if gender:
        qs = qs.filter(gender_eng__iexact=gender)
        
        # Apply STARTS WITH filters
    if first_starts:
        qs = qs.filter(first_name__istartswith=first_starts)
    
    if middle_starts:
        qs = qs.filter(middle_name__istartswith=middle_starts)
    
    if last_starts:
        qs = qs.filter(last_name__istartswith=last_starts)
    
    # Apply ENDS WITH filters
    if first_ends:
        qs = qs.filter(first_name__iendswith=first_ends)
    
    if middle_ends:
        qs = qs.filter(middle_name__iendswith=middle_ends)
    
    if last_ends:
        qs = qs.filter(last_name__iendswith=last_ends)
        
        
    # Pagination
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = []
    for v in page_obj:
        data.append({
            "voter_list_id": v.voter_list_id,
            "voter_name_eng": v.voter_name_eng,
            "voter_id": v.voter_id,
            "gender": v.gender_eng,
            "location": v.location,
            "badge": v.badge,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "kramank": v.kramank,
            "age":v.age_eng,
            "ward_id": v.ward_no
        })

    return JsonResponse({
        "status": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })
