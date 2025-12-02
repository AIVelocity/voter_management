from django.shortcuts import render
from django.shortcuts import render,HttpResponse
from django.http import JsonResponse
from .models import VoterList

def index(request):
    return JsonResponse ({
        "status": True,
        "message":"Application running"
    })
    
def voters_info(request):

    voters = VoterList.objects.select_related("tag_id").all()[:100]   # limit for safety

    data = []

    for v in voters:
        data.append({
            "voter_list_id": v.voter_list_id,
            "sr_no": v.sr_no,
            "voter_id": v.voter_id,
            "voter_name_marathi": v.voter_name_marathi,
            "voter_name_eng": v.voter_name_eng,
            "kramank": v.kramank,
            "address": v.address,
            "age": v.age,
            "gender": v.gender,
            "image_name": v.image_name,
            "ward_id": v.ward_id,
            "tag": v.tag_id.tag_name if v.tag_id else None
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })
