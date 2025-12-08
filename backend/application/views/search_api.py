from django.http import JsonResponse
from ..models import VoterList,VoterTag

import re
from collections import Counter

from django.db.models import Q
from django.core.paginator import Paginator


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

# search api
def voters_search(request):

    search = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    size = int(request.GET.get("size", 100))

    qs = VoterList.objects.select_related("tag_id")

    if search:
        qs = apply_dynamic_initial_search(qs, search)

    #  PATCH: if list → ordering must be Python side
    if isinstance(qs, list):
        qs.sort(key=lambda x: x.voter_list_id)

    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    data = [{
        "voter_list_id": v.voter_list_id,
        "voter_id": v.voter_id,
        "voter_name_eng": v.voter_name_eng,
        "age": v.age_eng,
        "gender": v.gender_eng,
        "ward_id": v.ward_no,
        "badge": v.badge,
        "tag": str(v.tag_id) if v.tag_id else None,
        # "badge":v.badge
    } for v in page_obj]

    return JsonResponse({
        "status": True,
        "query": search,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "records_returned": len(data),
        "data": data
    })
    
def family_dropdown_search(request):
    search = request.GET.get("search", "").strip()
    print(search)
    exclude_id = request.GET.get("exclude_id")   
    print(exclude_id)
    page = int(request.GET.get("page", 1))
    size = 30   

    qs = VoterList.objects.all()

    # Exclude the current voter (self cannot be father/mother)
    if exclude_id:
        qs = qs.exclude(voter_list_id=exclude_id)

    if search:
        qs = apply_dynamic_initial_search(qs, search)

    # If we got Python list back from search → sort manually
    if isinstance(qs, list):
        qs.sort(key=lambda x: x.voter_list_id)
    else:
        qs = qs.order_by("voter_list_id")

    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)

    results = [{
        "voter_list_id": v.voter_list_id,
        "voter_id": v.voter_id,
        "name": v.voter_name_eng,
        "age": v.age_eng,
        "gender": v.gender_eng,
        "ward": v.ward_no,
    } for v in page_obj]

    return JsonResponse({
        "status": True,
        "query": search,
        "exclude_id": exclude_id,
        "page": page,
        "page_size": size,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "results": results
    })

  
# def family_dropdown_search(request):
#     search = request.GET.get("search", "").strip()
    
#     page = int(request.GET.get("page", 1))
#     size = int(request.GET.get("size", 100))

#     qs = VoterList.objects.all()

#     if search:
#         qs = apply_dynamic_initial_search(qs, search)

#     # if Python list, sort it
#     if isinstance(qs, list):
#         qs.sort(key=lambda x: x.voter_list_id)

#         #  Limit to 30 only
#     paginator = Paginator(qs, size)
#     page_obj = paginator.get_page(page)

#     results = [{
#         "id": v.voter_list_id,
#         "voter_id": v.voter_id,
#         "name": v.voter_name_eng,
#         "age": v.age_eng,
#         "gender": v.gender_eng,
#         "ward": v.ward_no,
#     } for v in page_obj]

#     return JsonResponse({
#         "status": True,
#         "query": search,
#         "limit": 30,
#         "results": results
#     })
