import json
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def send_template(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    url = settings.MESSAGE_URL
    token = settings.ACCESS_TOKEN

    voter_number = "91" + "6306453375"
    template_name = "hello_world"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": voter_number,
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

    url = settings.MESSAGE_URL
    token = settings.ACCESS_TOKEN

    voter_number = "91" + "6306453375"
    message = "Hello from Django"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": voter_number,
        "type": "text",
        "text": {"body": message}
    }

    resp = requests.post(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }, json=payload)

    return JsonResponse({"status": True, "response": resp.json()})
