from whatsapp_service.models import Admin,SubAdmin,Volunteer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import random

def generate_key():
    return f"{random.randint(1111,9999)}"

@csrf_exempt
def registration(request):
    
    if request.method != "POST":
        return JsonResponse({
            "status":False,
            "message" : "Method must be POST"
        })
    
    try:
        body = json.loads(request.body)

        first_name = body.get("first_name")
        last_name = body.get("last_name")
        
        role = body.get("role")
        
        # admin_id = body.get("admin_id")
        # subadmin_id = body.get("subadmin_id")
        mobile_no = body.get("mobile_no")
        key = generate_key()
        activation_key = first_name[0] + last_name[0] + key
        
        if not role :
            return JsonResponse({
                "status":False,
                "message":"Role is required"
            })
        if not mobile_no:
            return JsonResponse({
                "status":False,
                "message":"Mobile Number is required"
            })
        
        # if not admin_id:
        #     return JsonResponse({
        #         "status":False,
        #         "message":"Admin ID is required"
        #     })
        
        role = role.lower()
        models = [Admin, SubAdmin, Volunteer]
        
        for m in models:
            if m.objects.filter(mobile_no=mobile_no).exists():
                return JsonResponse({
                    "status" : False,
                    "message" : f"Mobile number {mobile_no} already registered."
                })
        
        roles = ['subadmin','volunteer']
        
        if role in roles:
            if role == roles[0]:
                # admin = Admin.objects.filter(id=admin_id).first()
                obj = SubAdmin.objects.create(
                    # admin_pk=admin,
                    first_name=first_name,
                    # middle_name=middle,
                    last_name=last_name,
                    # full_name=full,
                    mobile_no=mobile_no,
                    activation_key=activation_key
                )
            elif role == roles[1]:
                # sa = SubAdmin.objects.filter(id=subadmin_id)
                obj = Volunteer.objects.create(
                    # subadmin_pk = sa,
                    first_name=first_name,
                    last_name=last_name,
                    mobile_no=mobile_no,
                    activation_key=activation_key
                )
                
            return JsonResponse({
                "status" : True,
                "message" : f"registered successfully",
                "activation_key": activation_key,
                "role" : role,
                "user_id" : obj.id
            })
                
    except Exception as e:
        return JsonResponse({
            "status" : False,
            "error" :str(e) 
        })