from whatsapp_service.models import Admin,SubAdmin,Volunteer
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def id_validation(request):
    
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "POST method required"}, status=405)
    
    try:
        body = json.loads(request.body)

        activation_key = body.get("activation_key")
        
        if not activation_key:
            return JsonResponse({
                "status":False,
                "message":"Activation Key Required"
            })
            
        admin = Admin.objects.filter(activation_key=activation_key).first()
        
        if admin:
            return JsonResponse({
                "status": True,
                "role" : "admin",
                "user_name": admin.first_name + admin.last_name,
                "message":"Activation key validated successfully"
            })
            
        subadmin = SubAdmin.objects.filter(activation_key=activation_key).first()
        
        if subadmin:
            return JsonResponse({
                "status": True,
                "role" : "subadmin",
                "user_name": subadmin.first_name + subadmin.last_name,
                "message":"Activation key validated successfully"
            })
            
        volunteer = Volunteer.objects.filter(activation_key=activation_key).first()
        
        if volunteer:
            return JsonResponse({
                "status": True,
                "role" : "volunteer",
                "user_name": volunteer.first_name + volunteer.last_name,
                "message":"Activation key validated successfully"
            })
            
        return JsonResponse({
            "status": False,
            "message": "Invalid activation key"
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": str(e)
        }, status=500)
    