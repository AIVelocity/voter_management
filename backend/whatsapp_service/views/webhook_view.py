import json
import logging
from django.conf import settings
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction

from application.models import VoterList
from ..models import VoterChatMessage

logger = logging.getLogger(__name__)
VERIFY_TOKEN = settings.VERIFY_TOKEN

def ok_resp():
    return JsonResponse({"status": True})

def error_resp(msg="error", status=400):
    return JsonResponse({"status": False, "message": msg}, status=status)


def _normalize_mobile_from_whatsapp(raw_from: str) -> str | None:
    if not raw_from:
        return None
    s = "".join(ch for ch in str(raw_from) if ch.isdigit())
    if len(s) == 10:
        return s
    if len(s) > 10:
        return s[2:]
    return None


def _resolve_voter_by_whatsapp_from(raw_from: str):
    """
    Try to find VoterList by normalized mobile_no. Returns VoterList instance or None.
    """
    mobile = _normalize_mobile_from_whatsapp(raw_from)
    if not mobile:
        return None
    try:
        return VoterList.objects.filter(mobile_no=mobile).first()
    except Exception as e:
        logger.exception("Error resolving voter by mobile %s: %s", mobile, e)
        return None


def _resolve_reply_to_db_id(context_id: str | None):
    """
    Resolve WA context.id (reply-to wa message id) into DB pk if present.
    """
    if not context_id:
        return None
    parent = VoterChatMessage.objects.filter(message_id=context_id).first()
    return parent.id if parent else None

# ----------------- handlers -----------------
def handle_statuses(statuses):
    """
    Update outgoing message status in DB by matching message_id.
    Expects list of status objects from WA webhook.
    """
    results = []
    for st in statuses:
        wa_id = st.get("id")
        new_status = st.get("status")
        if not wa_id or not new_status:
            logger.debug("Skipping incomplete status object: %s", st)
            results.append({"id": wa_id, "updated": False, "reason": "incomplete"})
            continue

        try:
            with transaction.atomic():
                chat = VoterChatMessage.objects.select_for_update().filter(message_id=wa_id).first()
                if not chat:
                    logger.info("Status update for unknown message_id=%s status=%s", wa_id, new_status)
                    results.append({"id": wa_id, "updated": False, "reason": "not_found"})
                    continue

                # Update status field
                prev = chat.status
                chat.status = new_status

                update_fields = ["status"]
                # Set read_at if WA says 'read'
                if new_status == "read":
                    chat.read_at = timezone.now()
                    update_fields.append("read_at")

                # Optionally, update sent_at if WA gives earlier timestamp and you want canonical send time
                # (commented out) if when and chat.sent_at is None: chat.sent_at = when; update_fields.append('sent_at')

                chat.save(update_fields=update_fields)
                logger.info("Updated chat id=%s message_id=%s %s -> %s", chat.id, wa_id, prev, new_status)
                results.append({"id": wa_id, "updated": True})
        except Exception as e:
            logger.exception("Failed to update status for %s: %s", wa_id, e)
            results.append({"id": wa_id, "updated": False, "error": str(e)})

    return {"results": results}


def handle_incoming_messages(messages, contacts=None):
    """
    Save incoming messages from voters in voter_chat_messages.
    messages: list of WA message objects.
    contacts: optional list of contact dicts (profile.name, wa_id, etc.)
    """
    saved = []
    for msg in messages:
        try:
            wa_message_id = msg.get("id")
            raw_from = msg.get("from")
            msg_type = msg.get("type") or "text"

            # extract contact name (if provided in contacts)
            contact_name = None
            if contacts:
                try:
                    contact_name = contacts[0].get("profile", {}).get("name")
                except Exception:
                    contact_name = None

            # text
            text_body = None
            if msg_type == "text":
                text_body = (msg.get("text") or {}).get("body")

            # location
            latitude = longitude = location_name = location_address = None
            if msg_type == "location":
                loc = msg.get("location") or {}
                latitude = str(loc.get("latitude")) if loc.get("latitude") is not None else None
                longitude = str(loc.get("longitude")) if loc.get("longitude") is not None else None
                location_name = loc.get("name")
                location_address = loc.get("address")

            # media (image/video/audio/document)
            media_type = None
            media_id = None
            file_name = None
            media_url = None
            for t in ("image", "video", "audio", "document"):
                if t == msg_type and t in msg:
                    media_type = t
                    payload = msg.get(t) or {}
                    media_id = payload.get("id")
                    file_name = payload.get("filename") or None
                    # webhook typically doesn't include direct media url
                    break

            # context (reply-to)
            context_id = (msg.get("context") or {}).get("id")
            reply_to_db_id = _resolve_reply_to_db_id(context_id)

            # map 'from' to voter (if found)
            voter = _resolve_voter_by_whatsapp_from(raw_from)
            voter_id = voter.voter_list_id if voter else None
            sent_at = timezone.now()
            # Build DB kwargs
            instance_kwargs = {
                "message_id": wa_message_id or f"incoming_local:{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
                "voter_id": voter_id,
                "sender": "voter",
                "status": "received",
                "message": text_body if text_body else (contact_name if contact_name else None),
                "type": media_type or (msg_type or "text"),
                "media_id": media_id,
                "media_url": media_url,
                "file_name": file_name,
                "latitude": latitude,
                "longitude": longitude,
                "location_name": location_name,
                "location_address": location_address,
                "reply_to_id": reply_to_db_id,
                "sent_at": sent_at,
            }

            with transaction.atomic():
                chat_row = VoterChatMessage.objects.create(**instance_kwargs)

            logger.info("Saved incoming msg wa_id=%s db_id=%s from=%s type=%s voter_id=%s",
                        wa_message_id, chat_row.id, raw_from, msg_type, voter_id)
            saved.append({"wa_id": wa_message_id, "db_id": chat_row.id, "voter_id": voter_id})
        except Exception as e:
            logger.exception("Failed to save incoming message: %s", e)
            saved.append({"error": str(e), "raw_msg": msg.get("id")})

    return {"saved": saved}

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
