from ..models import VoterTag
from django.http import JsonResponse


# index api
def index(request):
    return JsonResponse ({
        "status": True,
        "message":"Application running"
    })
    
# tags api
def tags(request):
    tags = VoterTag.objects.all().order_by("tag_id")
    data = []
    for tag in tags:
        data.append({
            "tag_id":tag.tag_id,
            "tag_name":tag.tag_name,
        })
    return JsonResponse({
        "status":True,
        "data":data
    })