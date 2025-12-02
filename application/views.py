from django.http import JsonResponse
from .models import VoterList

def index(request):
    return JsonResponse ({
        "status": True,
        "message":"Application running"
    })

# all voters list 
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
            # "age": v.age,
            # "gender": v.gender,
            "age":v.age_eng,
            "gender":v.gender_eng,
            # "image_name": v.image_name,
            "ward_id": v.ward_id,
            "tag": v.tag_id.tag_name if v.tag_id else None
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })

# single voter info page
def single_voters_info(request, voter_list_id):

    try:
        voter = VoterList.objects.select_related("tag_id").get(
            voter_list_id=voter_list_id
        )

    except VoterList.DoesNotExist:
        return JsonResponse({
            "status": False,
            "message": "Voter not found"
        }, status=404)

    data = {
        "voter_list_id": voter.voter_list_id,
        "sr_no": voter.sr_no,
        "voter_id": voter.voter_id,
        "voter_name_marathi": voter.voter_name_marathi,
        "voter_name_eng": voter.voter_name_eng,
        "kramank": voter.kramank,
        "address": voter.address,
        # "age": voter.age,
        # "gender": voter.gender,
        "age":voter.age_eng,
        "gender":voter.gender_eng,
        # "image_name": voter.image_name,
        "ward_id": voter.ward_id,
        "tag": voter.tag_id.tag_name if voter.tag_id else None
    }

    return JsonResponse({
        "status": True,
        "data": data
    })
