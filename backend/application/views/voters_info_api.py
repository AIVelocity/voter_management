from django.http import JsonResponse
from ..models import VoterList,VoterTag

from django.core.paginator import Paginator

def voters_info(request):

    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))

    qs = VoterList.objects.select_related("tag_id") \
            .order_by("ward_no", "voter_list_id")

    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = []

    for v in page_obj:
        data.append({
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

    return JsonResponse({
        "status": True,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })