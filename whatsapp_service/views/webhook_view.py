import json
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

VERIFY_TOKEN = settings.VERIFY_TOKEN
def ok_resp():
    return JsonResponse({"status": True})

def error_resp(msg="error", status=400):
    return JsonResponse({"status": False, "message": msg}, status=status)


# ---- Handlers (separate, testable functions) ----
def handle_statuses(statuses):
    """
    Process list of status objects (delivery/read updates).
    Currently just logs them. Return None or dict if you want to return info.
    """
    for status in statuses:
        wa_message_id = status.get("id")
        new_status = status.get("status")
        recipient = status.get("recipient_id") or status.get("to")
        logger.info("STATUS: id=%s status=%s recipient=%s", wa_message_id, new_status, recipient)
    return None


def handle_incoming_messages(messages, contacts=None):
    """
    Process list of message objects.
    messages: list of message dicts
    contacts: list of contact dicts (optional)
    """
    for message in messages:
        wa_message_id = message.get("id")
        client_from = message.get("from")
        mtype = message.get("type") or "unknown"
        text = (message.get("text") or {}).get("body") if mtype == "text" else None

        # minimal media detection
        media = {}
        for t in ("image", "video", "audio", "document", "location"):
            if t in message:
                media = {"type": t, "payload": message.get(t)}
                break

        contact_name = None
        if contacts:
            try:
                contact_name = contacts[0].get("profile", {}).get("name")
            except Exception:
                contact_name = None

        logger.info(
            "MSG: id=%s from=%s type=%s text=%s contact=%s media=%s",
            wa_message_id, client_from, mtype, text, contact_name, bool(media)
        )
    return None


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

    for entry in entries:
        changes = entry.get("changes", []) or []
        for change in changes:
            value = change.get("value", {}) or {}

            # Status updates
            statuses = value.get("statuses")
            if statuses:
                handle_statuses(statuses)
                # continue (statuses may be sent independently)
                continue

            # Incoming messages
            messages = value.get("messages") or []
            contacts = value.get("contacts") or []
            if messages:
                handle_incoming_messages(messages, contacts=contacts)
                continue

            logger.debug("Unhandled change value: %s", value)

    return ok_resp()
