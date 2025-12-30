from ..models import VoterTag,Roles
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# index api
def index(request):
    return JsonResponse ({
        "status": True,
        "message":"Application running"
    })
    


@api_view(["GET"])
@permission_classes([IsAuthenticated])
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
    
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def roles(request):
    roles = Roles.objects.all().order_by("role_id")
    data = []
    for r in roles:
        data.append({
            "role_id" : r.role_id,
            "role_name" : r.role_name
        })
    
    return JsonResponse({
        "status":True,
        "data": data
    })
    