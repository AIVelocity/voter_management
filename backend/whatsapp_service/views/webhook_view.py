import json
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..utils.webhook_handler import handle_incoming_messages, handle_statuses, parse_whatsapp_error

logger = logging.getLogger(__name__)
VERIFY_TOKEN = settings.VERIFY_TOKEN


def ok_resp():
    return JsonResponse({"status": True}, status=200)


def error_resp(msg="error", status=400):
    return JsonResponse({"status": False, "message": msg}, status=status)


# ------------------------------
# GET HANDLER (unchanged)
# ------------------------------
def verify_webhook(request):
    hub_mode = request.GET.get("hub.mode")
    hub_token = request.GET.get("hub.verify_token")
    hub_challenge = request.GET.get("hub.challenge")
    expected = VERIFY_TOKEN

    if hub_mode == "subscribe" and hub_token == expected:
        print("Webhook verified")
        return HttpResponse(hub_challenge, status=200)

    return error_resp("Invalid verification token", status=403)


# ------------------------------
# POST HANDLER (unchanged)
# ------------------------------
def receive_webhook(request):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
        logger.debug("Webhook body: %s", body)
    except json.JSONDecodeError:
        logger.error("Bad JSON in webhook payload")
        return error_resp("Invalid JSON", status=400)

    entries = body.get("entry", [])
    if not entries:
        logger.debug("Empty entry")
        return ok_resp()

    overall_results = {"statuses": [], "incoming": [], "errors": []}

    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {}) or {}

            # Status updates
            statuses = value.get("statuses")
            if statuses:
                try:
                    res = handle_statuses(statuses)
                    overall_results["statuses"].append({"ok": True, "result": res})
                except Exception as exc:
                    msg = parse_whatsapp_error({"error": {"message": str(exc)}})
                    overall_results["statuses"].append({"ok": False, "error": msg})
                continue

            # Incoming messages
            messages = value.get("messages") or []
            contacts = value.get("contacts") or []

            if messages:
                try:
                    res = handle_incoming_messages(messages, contacts=contacts)
                    overall_results["incoming"].append({"ok": True, "result": res})
                except Exception as exc:
                    msg = parse_whatsapp_error({"error": {"message": str(exc)}})
                    overall_results["incoming"].append({"ok": False, "error": msg})
                continue

            overall_results.setdefault("unhandled", []).append(value)

    return ok_resp()


# ------------------------------
# MAIN WRAPPER (this is the ONLY new thing)
# ------------------------------
@csrf_exempt
def whatsapp_webhook(request):
    """
    Meta requires GET (verification) + POST (messages) on SAME URL.
    Wrapper routes requests to the correct internal handler.
    """
    if request.method == "GET":
        return verify_webhook(request)

    if request.method == "POST":
        return receive_webhook(request)

    return error_resp("Invalid method", status=405)
