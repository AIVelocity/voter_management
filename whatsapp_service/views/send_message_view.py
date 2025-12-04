import json
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


url = settings.MESSAGE_URL
token = settings.ACCESS_TOKEN

@csrf_exempt
def send_template(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except:
        data = request.POST

    voter_number = data.get("phone_number")
    template_name = data.get("template_name")
    if not voter_number or not template_name:
        return JsonResponse({"status": False, "message": "number and template_name required"}, status=400)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "91" + voter_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"}
        }
    }

    resp = requests.post(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }, json=payload)

    return JsonResponse({"status": True, "response": resp.json()})


@csrf_exempt
def send_text(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)
    try:
        data = json.loads(request.body)
    except:
        data = request.POST

    voter_number = data.get("phone_number")  
    message = data.get("message")  

    if not voter_number or not message:
        return JsonResponse({"status": False, "message": "number and message required"}, status=400)


    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "91" + voter_number,
        "type": "text",
        "text": {"body": message}
    }

    resp = requests.post(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }, json=payload)

    return JsonResponse({"status": True, "response": resp.json()})
