import time
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..utils import parse_request_body, _chunked, _clean_phone, get_recipients_from_request, send_whatapps_request

from application.models import VoterList
from ..models import VoterChatMessage, TemplateName

url = settings.MESSAGE_URL
token = settings.ACCESS_TOKEN

# --- CONFIG: provider limit ---
PROVIDER_MAX_PER_SECOND = 50  # provider limit (messages / sec)
DEFAULT_CHUNK_SIZE = PROVIDER_MAX_PER_SECOND  # how many messages to send per second
country_code = "91"

# --- Views that use chunking to obey provider rate limits ---
@csrf_exempt
def send_template(request):
    
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    recipients, errors = get_recipients_from_request(request)
    if not recipients:
        return JsonResponse({"status": False, "message": "No recipients", "errors": errors}, status=400)

    data = parse_request_body(request)
    template_id = data.get("id")
    if not template_id:
        return JsonResponse({"status": False, "message": "template_id required"}, status=400)

    try:
        template = TemplateName.objects.get(id=template_id)
    except TemplateName.DoesNotExist:
        return JsonResponse({"status": False, "message": "Template not found"}, status=404)

    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")
    reply_to = data.get("reply_to_message_id")
    chunk_size = data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    # Build a per-recipient list of payloads + voters
    tasks = []
    for v in recipients:
        phone = _clean_phone(getattr(v, "mobile_no", None))
        if not phone:
            errors.append(f"No phone for voter_list_id {getattr(v, 'voter_list_id', None)} - skipped")
            continue
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": country_code + phone,
            "type": "template",
            "template": {"name": template.name, "language": {"code": "en_US"}}
        }
        tasks.append((payload, v))

    # Send tasks in chunks respecting provider limit
    results = []
    total = len(tasks)
    if total == 0:
        return JsonResponse({"status": False, "message": "No valid recipients after validation", "errors": errors}, status=400)

    for chunk_index, chunk in enumerate(_chunked(tasks, chunk_size)):
        start_ts = time.time()
        for payload, voter in chunk:
            res = send_whatapps_request(payload, voter,
                                        message=template.name,
                                        message_type="template",
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        reply_to_message_id=reply_to)
            results.append({
                "recipient_voter_list_id": getattr(voter, "voter_list_id", None),
                "recipient_phone": payload.get("to"),
                **res
            })
        # Enforce per-second rate limit: wait until 1 second elapsed since start of chunk
        elapsed = time.time() - start_ts
        if elapsed < 1.0:
            to_sleep = 1.0 - elapsed
            # do not sleep after last chunk
            if (chunk_index + 1) * chunk_size < total:
                time.sleep(to_sleep)

    return JsonResponse({"status": True, "template": template.name, "errors": errors, "results": results, "sent_count": len(results)}, status=200)


@csrf_exempt
def send_text(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    recipients, errors = get_recipients_from_request(request)
    if not recipients:
        return JsonResponse({"status": False, "message": "No recipients", "errors": errors}, status=400)

    data = parse_request_body(request)
    message = data.get("message")
    if not message:
        return JsonResponse({"status": False, "message": "message required"}, status=400)

    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")
    reply_to = data.get("reply_to_message_id")
    chunk_size = data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    tasks = []
    for v in recipients:
        phone = _clean_phone(getattr(v, "mobile_no", None))
        if not phone:
            errors.append(f"No phone for voter_list_id {getattr(v, 'voter_list_id', None)} - skipped")
            continue
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": country_code + phone,
            "type": "text",
            "text": {"body": message}
        }
        tasks.append((payload, v))

    results = []
    total = len(tasks)
    if total == 0:
        return JsonResponse({"status": False, "message": "No valid recipients after validation", "errors": errors}, status=400)

    for chunk_index, chunk in enumerate(_chunked(tasks, chunk_size)):
        start_ts = time.time()
        for payload, voter in chunk:
            res = send_whatapps_request(payload, voter,
                                        message=message,
                                        message_type="text",
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        reply_to_message_id=reply_to)
            results.append({
                "recipient_voter_list_id": getattr(voter, "voter_list_id", None),
                "recipient_phone": payload.get("to"),
                **res
            })
        # Enforce per-second rate limit: wait until 1 second elapsed since start of chunk
        elapsed = time.time() - start_ts
        if elapsed < 1.0:
            to_sleep = 1.0 - elapsed
            if (chunk_index + 1) * chunk_size < total:
                time.sleep(to_sleep)

    return JsonResponse({"status": True, "message_text": message, "errors": errors, "results": results, "sent_count": len(results)}, status=200)


# --- Media send endpoints (image/audio/video/document) ---
@csrf_exempt
def send_image(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    recipients, errors = get_recipients_from_request(request)
    if not recipients:
        return JsonResponse({"status": False, "message": "No recipients", "errors": errors}, status=400)

    data = parse_request_body(request)
    media_id = data.get("media_id")
    media_url = data.get("media_url")
    if not media_id:
        return JsonResponse({"status": False, "message": "media_id required for image"}, status=400)

    caption = data.get("caption")
    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")
    reply_to = data.get("reply_to_message_id")
    chunk_size = data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    tasks = []
    for v in recipients:
        phone = _clean_phone(getattr(v, "mobile_no", None))
        if not phone:
            errors.append(f"No phone for voter_list_id {getattr(v, 'voter_list_id', None)} - skipped")
            continue
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": country_code + phone,
            "type": "image",
            "image": {"id": media_id}
        }
        if caption:
            payload["image"]["caption"] = caption
        tasks.append((payload, v))

    results = []
    total = len(tasks)
    if total == 0:
        return JsonResponse({"status": False, "message": "No valid recipients after validation", "errors": errors}, status=400)

    for chunk_index, chunk in enumerate(_chunked(tasks, chunk_size)):
        start_ts = time.time()
        for payload, voter in chunk:
            res = send_whatapps_request(payload, voter,
                                        message=caption or "",
                                        message_type="image",
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        media_id=media_id,
                                        media_url=media_url,
                                        reply_to_message_id=reply_to)
            results.append({
                "recipient_voter_list_id": getattr(voter, "voter_list_id", None),
                "recipient_phone": payload.get("to"),
                **res
            })
        elapsed = time.time() - start_ts
        if elapsed < 1.0:
            # do not sleep after last chunk
            if (chunk_index + 1) * chunk_size < total:
                time.sleep(1.0 - elapsed)

    return JsonResponse({"status": True, "message_type": "image", "errors": errors, "results": results, "sent_count": len(results)}, status=200)


@csrf_exempt
def send_audio(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    recipients, errors = get_recipients_from_request(request)
    if not recipients:
        return JsonResponse({"status": False, "message": "No recipients", "errors": errors}, status=400)

    data = parse_request_body(request)
    media_id = data.get("media_id")
    if not media_id:
        return JsonResponse({"status": False, "message": "media_id required for audio"}, status=400)

    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")
    reply_to = data.get("reply_to_message_id")
    chunk_size = data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    tasks = []
    for v in recipients:
        phone = _clean_phone(getattr(v, "mobile_no", None))
        if not phone:
            errors.append(f"No phone for voter_list_id {getattr(v, 'voter_list_id', None)} - skipped")
            continue
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": country_code + phone,
            "type": "audio",
            "audio": {"id": media_id}
        }
        tasks.append((payload, v))

    results = []
    total = len(tasks)
    if total == 0:
        return JsonResponse({"status": False, "message": "No valid recipients after validation", "errors": errors}, status=400)

    for chunk_index, chunk in enumerate(_chunked(tasks, chunk_size)):
        start_ts = time.time()
        for payload, voter in chunk:
            res = send_whatapps_request(payload, voter,
                                        message=None,
                                        message_type="audio",
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        media_id=media_id,
                                        media_url=data.get("media_url"),
                                        reply_to_message_id=reply_to)
            results.append({
                "recipient_voter_list_id": getattr(voter, "voter_list_id", None),
                "recipient_phone": payload.get("to"),
                **res
            })
        elapsed = time.time() - start_ts
        if elapsed < 1.0:
            if (chunk_index + 1) * chunk_size < total:
                time.sleep(1.0 - elapsed)

    return JsonResponse({"status": True, "message_type": "audio", "errors": errors, "results": results, "sent_count": len(results)}, status=200)


@csrf_exempt
def send_document(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    recipients, errors = get_recipients_from_request(request)
    if not recipients:
        return JsonResponse({"status": False, "message": "No recipients", "errors": errors}, status=400)

    data = parse_request_body(request)
    media_id = data.get("media_id")
    if not media_id:
        return JsonResponse({"status": False, "message": "media_id required for document"}, status=400)

    caption = data.get("caption")
    file_name = data.get("file_name")
    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")
    reply_to = data.get("reply_to_message_id")
    chunk_size = data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    tasks = []
    for v in recipients:
        phone = _clean_phone(getattr(v, "mobile_no", None))
        if not phone:
            errors.append(f"No phone for voter_list_id {getattr(v, 'voter_list_id', None)} - skipped")
            continue
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": country_code + phone,
            "type": "document",
            "document": {"id": media_id}
        }
        if caption:
            payload["document"]["caption"] = caption
        if file_name:
            payload["document"]["filename"] = file_name
        tasks.append((payload, v))

    results = []
    total = len(tasks)
    if total == 0:
        return JsonResponse({"status": False, "message": "No valid recipients after validation", "errors": errors}, status=400)

    for chunk_index, chunk in enumerate(_chunked(tasks, chunk_size)):
        start_ts = time.time()
        for payload, voter in chunk:
            res = send_whatapps_request(payload, voter,
                                        message=caption or file_name or "",
                                        message_type="document",
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        media_id=media_id,
                                        media_url=data.get("media_url"),
                                        reply_to_message_id=reply_to)
            results.append({
                "recipient_voter_list_id": getattr(voter, "voter_list_id", None),
                "recipient_phone": payload.get("to"),
                **res
            })
        elapsed = time.time() - start_ts
        if elapsed < 1.0:
            if (chunk_index + 1) * chunk_size < total:
                time.sleep(1.0 - elapsed)

    return JsonResponse({"status": True, "message_type": "document", "errors": errors, "results": results, "sent_count": len(results)}, status=200)


@csrf_exempt
def send_video(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Only POST allowed"}, status=405)

    recipients, errors = get_recipients_from_request(request)
    if not recipients:
        return JsonResponse({"status": False, "message": "No recipients", "errors": errors}, status=400)

    data = parse_request_body(request)
    media_id = data.get("media_id")
    if not media_id:
        return JsonResponse({"status": False, "message": "media_id required for video"}, status=400)

    caption = data.get("caption")
    sender_type = data.get("sender_type")
    sender_id = data.get("sender_id")
    reply_to = data.get("reply_to_message_id")
    chunk_size = data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    tasks = []
    for v in recipients:
        phone = _clean_phone(getattr(v, "mobile_no", None))
        if not phone:
            errors.append(f"No phone for voter_list_id {getattr(v, 'voter_list_id', None)} - skipped")
            continue
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": country_code + phone,
            "type": "video",
            "video": {"id": media_id}
        }
        if caption:
            payload["video"]["caption"] = caption
        tasks.append((payload, v))

    results = []
    total = len(tasks)
    if total == 0:
        return JsonResponse({"status": False, "message": "No valid recipients after validation", "errors": errors}, status=400)

    for chunk_index, chunk in enumerate(_chunked(tasks, chunk_size)):
        start_ts = time.time()
        for payload, voter in chunk:
            res = send_whatapps_request(payload, voter,
                                        message=caption or "",
                                        message_type="video",
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        media_id=media_id,
                                        media_url=data.get("media_url"),
                                        reply_to_message_id=reply_to)
            results.append({
                "recipient_voter_list_id": getattr(voter, "voter_list_id", None),
                "recipient_phone": payload.get("to"),
                **res
            })
        elapsed = time.time() - start_ts
        if elapsed < 1.0:
            if (chunk_index + 1) * chunk_size < total:
                time.sleep(1.0 - elapsed)

    return JsonResponse({"status": True, "message_type": "video", "errors": errors, "results": results, "sent_count": len(results)}, status=200)


@require_http_methods(["GET"])
def get_messages_for_voter(request):
    voter_list_id = request.GET.get("voter_list_id")
    if not voter_list_id:
        return JsonResponse({"status": False, "message": "voter_list_id required"}, status=400)

    # get voter
    try:
        voter = VoterList.objects.get(voter_list_id=voter_list_id)
    except VoterList.DoesNotExist:
        return JsonResponse({"status": False, "message": "Voter not found"}, status=404)

    # get messages
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


@csrf_exempt
def get_all_templates(request):
    if request.method != "GET":
        return JsonResponse({"status": False, "message": "Only GET method allowed"}, status=405)

    templates = TemplateName.objects.all().values("id", "name")

    return JsonResponse({
        "status": True,
        "count": templates.count(),
        "templates": list(templates)
    }, status=200)