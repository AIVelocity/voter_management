from ..models import Occupation
from django.http import JsonResponse

def occupation_dropdown(request):
    
    data = list(Occupation.objects.all()
                .values("occupation_id","occupation_name")
                .order_by("occupation_id")
                )
    
    return JsonResponse({
        "status":True,
        "data":data
    })