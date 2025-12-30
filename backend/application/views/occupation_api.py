from ..models import Occupation
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def occupation_dropdown(request):
    
    data = list(Occupation.objects.all()
                .values("occupation_id","occupation_name")
                .order_by("occupation_id")
                )
    
    return JsonResponse({
        "status":True,
        "data":data
    })