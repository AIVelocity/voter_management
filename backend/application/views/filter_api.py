from ..models import VoterList
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse

def filter(request):
    
    page = int(request.GET.get("page",1))
    size = int(request.GET.get("size",50))
    
    search = request.GET.get("search")
    
    first_name = request.GET.get("first_name")
    middle_name = request.GET.get("last_name")
    last_name = request.GET.get("last_name")
    
    age_max = request.GET.get("age_max")
    age_min = request.GET.get("age_min")
    
    location = request.GET.get("location")
    tag = request.GET.get("tag_id")
    
    qs = VoterList.objects.select_related("tag_id").all()
    
    if search:
        tokens = search.lower().split()
        search_q = Q()
        for t in tokens:
            search_q &= (
                Q(first_name__icontains =t)|
                Q(middle_name__icontains=t)|
                Q(last_name__icontains = t)
            )
        qs = qs.filter(search_q)
        
    if first_name:
        qs = qs.contains(first_name__icontains=first_name)
    
    if middle_name:
        qs = qs.contains(middle_name__icontains=middle_name)
    
    if last_name:
        qs = qs.contains(last_name__icontains=last_name)
    
    if age_max:
        qs = qs.filter(age_eng__lte=age_max)
    
    if age_min:
        qs = qs.filter(age_eng__gte=age_min)
        
    if location:
        qs = qs.contains(location__icontains = location)
    
    if tag:
        qs = qs.contains(tag_id__id=tag)
    
    pagintor = Paginator(qs,size)
    page_obj = pagintor.get_page(page)
    
    data =[]
    for v in page_obj:
        data.append({
            "voter_list_id": v.voter_list_id,
            "voter_name_eng" : v.voter_name_eng,
            "voter_id" :v.voter_id,
            "gender" : v.gender_eng,
            "location" :v.location,
            "badge" : v.badge,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "kramank" : v.kramank,
            "ward_id" :v.ward_no
        })
    return JsonResponse({
        "status":True,
        "page":page,
        "page_size":size,
        "total_pages":pagintor.num_pages,
        "total_records" : pagintor.count,
        "records_returned" : len(data),
        "data":data
    })