import json
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..utils.webhook_handler import handle_incoming_messages, handle_statuses

logger = logging.getLogger(__name__)
VERIFY_TOKEN = settings.VERIFY_TOKEN

def ok_resp():
    return JsonResponse({"status": True})

def error_resp(msg="error", status=400):
    return JsonResponse({"status": False, "message": msg}, status=status)


# ---- Main webhook view (dispatches to handlers) ----
@require_http_methods(["GET"])
def verify_webhook(request):
    hub_mode = request.GET.get("hub.mode")
    hub_token = request.GET.get("hub.verify_token")
    hub_challenge = request.GET.get("hub.challenge")
    expected = VERIFY_TOKEN
    if hub_mode == "subscribe" and hub_token == expected:
        return HttpResponse(hub_challenge, status=200)
    return error_resp("Invalid verification token", status=403)


@csrf_exempt
@require_http_methods(["POST"])
def receive_webhook(request):
    # single entry point for WhatsApp — parse and dispatch to handler funcs
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
        print(body)
        logger.debug("Webhook body: %s", body)
    except json.JSONDecodeError:
        logger.exception("Bad JSON")
        return error_resp("Invalid JSON", status=400)

    entries = body.get("entry", [])
    if not entries:
        logger.debug("Empty entry")
        return ok_resp()
    
    overall_results = {"statuses": [], "incoming": []}
    for entry in entries:
        changes = (entry.get("changes") or [])[:]
        for change in changes:
            value = change.get("value", {}) or {}

            # Status updates
            statuses = value.get("statuses")
            if statuses:
                res = handle_statuses(statuses)
                overall_results["statuses"].append(res)
                # statuses may be delivered separately from messages
                continue

            # Incoming messages
            messages = value.get("messages") or []
            contacts = value.get("contacts") or []
            if messages:
                res = handle_incoming_messages(messages, contacts=contacts)
                overall_results["incoming"].append(res)
                continue

            logger.debug("Unhandled change value: %s", value)

    return ok_resp()
