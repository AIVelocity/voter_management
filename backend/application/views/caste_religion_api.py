from django.http import JsonResponse
from ..models import Religion,Caste

def religion_dropdown(request):
    data = list(Religion.objects.all()
                .values("religion_id","religion_name")
                .order_by("religion_id")
                )
    return JsonResponse({
        "status":True,
        "data" : data
    })
    
def caste_dropdown(request):
    
    religion_id = request.GET.get("religion_id")
    
    if not religion_id:
        return JsonResponse({
            "status" : False,
            "message": "Religion ID is required"
        },status = 400)
        
    data = list(Caste.objects.all()
                .values("religion_id","caste_id","caste_name")
                .order_by("caste_id")
                )
    
    return JsonResponse({
        "status" : True,
        "data" : data
    })