from django.http import JsonResponse
from ..models import Religion,Caste
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def religion_dropdown(request):
    data = list(Religion.objects.all()
                .values("religion_id","religion_name")
                .order_by("religion_id")
                )
    return JsonResponse({
        "status":True,
        "data" : data
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def caste_dropdown(request):
    
    religion_id = request.GET.get("religion_id")
    
    if not religion_id:
        return JsonResponse({
            "status" : False,
            "message": "Religion ID is required"
        },status = 400)
        
    data = list(Caste.objects.filter(religion_id=religion_id)
                .values("religion_id","caste_id","caste_name")
                .order_by("caste_id")
                )
    
    return JsonResponse({
        "status" : True,
        "data" : data
    })