import json
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from application.models import VoterList
from ..models import TemplateName, VoterChatMessage


url = settings.MESSAGE_URL
token = settings.ACCESS_TOKEN

def parse_request_body(request):
    try:
        data = json.loads(request.body)
    except:
        data = request.POST
    return data

def validate_users(request):
    data = parse_request_body(request)

    voter_list_id = data.get("voter_list_id")
    if not voter_list_id:
        return JsonResponse({"status": False, "message": "voter_list_id required"}, status=400)
    # Fetch phone number from VoterList
    try:
        voter = VoterList.objects.get(voter_list_id=voter_list_id)
    except VoterList.DoesNotExist:
        return JsonResponse({"status": False, "message": "Voter not found"}, status=404)
    return voter 

def _resolve_reply_to(reply_to_message_id):
    """
    Keep this as you requested — resolves a WA message_id -> db.pk
    """
    if not reply_to_message_id:
        return None
    parent = VoterChatMessage.objects.filter(message_id=reply_to_message_id).first()
    return parent.id if parent else None


def _make_fallback_local_id():
    """Only used when WA call fails and we MUST insert a unique message_id in DB."""
    return f"local:{timezone.now().strftime('%Y%m%d%H%M%S%f')}:{uuid.uuid4().hex[:8]}"

def send_whatapps_request(payload, voter,message=None,
                          message_type="text",
                          sender_type: str | None = None,
                          sender_id: int | None = None,
                          media_id: str | None = None,
                          media_url: str | None = None,
                          reply_to_message_id: str | None = None):
    if not sender_type:
        return JsonResponse({"status": False, "message": "sender_type required"}, status=400)
    if sender_type in ("admin", "sub-admin") and not sender_id:
        return JsonResponse({"status": False, "message": "sender_id required for admin/sub-admin"}, status=400)

    try:
        resp = requests.post(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=payload)
    except Exception as e:
        response_json = {"error": str(e)}
        resp_status = 0
        wa_message_id = None
    else:
        resp_status = resp.status_code
        try:
            response_json = resp.json()
        except Exception:
            response_json = {"raw_text": resp.text}
        # extract wa id if present
        wa_message_id = None
        if resp_status < 400:
            try:
                wa_message_id = response_json.get("messages", [])[0].get("id")
            except Exception:
                wa_message_id = None
    reply_to_db_id = _resolve_reply_to(reply_to_message_id)

    # Prepare DB row fields. If WA returned id -> use it; else use fallback local id
    if wa_message_id:
        db_message_id = wa_message_id
        db_status = "sent" if resp_status < 400 else "failed"
    else:
        db_message_id = _make_fallback_local_id()
        db_status = "failed" if resp_status == 0 or resp_status >= 400 else "sent"

    # Build kwargs to create VoterChatMessage
    instance_kwargs = {
        "message_id": db_message_id,
        "voter_id": voter.voter_list_id if voter else None,
        "sender": sender_type,
        "status": db_status,
        "message": message,
        "type": message_type,
        "media_id": media_id,
        "media_url": media_url,
        "sent_at": timezone.now(),
    }

    if sender_type == "admin":
        instance_kwargs["admin_id"] = sender_id
    elif sender_type == "sub-admin":
        instance_kwargs["subadmin_id"] = sender_id
    else:
        return JsonResponse({"status": False, "message": "Invalid sender_type"}, status=400)
    if reply_to_db_id:
        instance_kwargs["reply_to_id"] = reply_to_db_id

    # Save DB row
    try:
        with transaction.atomic():
            chat_row = VoterChatMessage.objects.create(**instance_kwargs)
    except Exception as e:
        return JsonResponse({"status": False, "message": f"DB error: {str(e)}"}, status=500)

    return JsonResponse({
        "status": True if resp_status and resp_status < 400 else False,
        "whatsapp_response": response_json,
    }, status=200 if resp_status and resp_status < 400 else 502)
    

@csrf_exempt
def send_template(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)
    
    voter = validate_users(request)
    data = parse_request_body(request)

    template_id = data.get("id")
    if not template_id:
        return JsonResponse({"status": False, "message": "template_id required"}, status=400)
    
    # Fetch template name from TemplateName
    try:
        template = TemplateName.objects.get(id=template_id)
    except TemplateName.DoesNotExist:
        return JsonResponse({"status": False, "message": "Template not found"}, status=404)

    phone_number = voter.mobile_no
    template_name = template.name

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "91" + phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"}
        }
    }
    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")

    return send_whatapps_request(payload, voter,message=template.name,
        message_type="template",
        sender_type=sender_type,
        sender_id=sender_id,
        reply_to_message_id=data.get("reply_to_message_id"))


@csrf_exempt
def send_text(request):
    """
    Use a message template to re-engage with the customer.
    otherwise, below error will occur:
    Message failed to send because more than 24 hours have passed since the customer last replied to this number.

    """
    
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)
    
    voter = validate_users(request)
    data = parse_request_body(request)

    message = data.get("message")
    if not message:
        return JsonResponse({"status": False, "message": "message required"}, status=400)

    phone_number = voter.mobile_no

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "91" + phone_number,
        "type": "text",
        "text": {"body": message}
    }

    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")

    return send_whatapps_request(payload, voter,message=message,
        message_type="text",
        sender_type=sender_type,
        sender_id=sender_id,
        reply_to_message_id=data.get("reply_to_message_id"))



@require_http_methods(["GET"])
def get_messages_for_voter(request):
    voter_list_id = request.GET.get("voter_list_id")
    print("voter_list_id",voter_list_id)
    if not voter_list_id:
        return JsonResponse({"status": False, "message": "voter_list_id required"}, status=400)

    # get voter
    try:
        voter = VoterList.objects.get(voter_list_id=voter_list_id)
    except VoterList.DoesNotExist:
        return JsonResponse({"status": False, "message": "Voter not found"}, status=404)

    # EXACT REFERENCE STYLE QUERY
    messages_qs = (
        VoterChatMessage.objects
        .filter(voter_id=voter.voter_list_id)
        .order_by("sent_at")
    )

    messages = []
    for m in messages_qs:
        messages.append({
            "id": m.id,
            "message_id": m.message_id,
            "sender": m.sender,
            "status": m.status,
            "message": m.message,
            "type": m.type,
            "media_id": m.media_id,
            "media_url": m.media_url,
            "file_name": m.file_name,
            "reply_to_id": m.reply_to_id,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "read_at": m.read_at.isoformat() if m.read_at else None,
        })

    return JsonResponse({
        "messages": messages
    }, safe=False)