import logging
import mimetypes
import os
from io import BytesIO

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from application.models import VoterList
from ..models import VoterChatMessage
from .download_whatsapp_media import download_whatsapp_media
from .s3_integration import upload_to_s3

logger = logging.getLogger(__name__)



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
    if not context_id or not VoterChatMessage:
        return None
    parent = VoterChatMessage.objects.filter(message_id=context_id).first()
    return parent.id if parent else None


def _safe_extension_from_mime(mime: str | None, fallback: str = "bin") -> str:
    if not mime:
        return fallback
    ext = mimetypes.guess_extension(mime) or ""
    return ext.lstrip(".") or fallback


# ----------------- handlers -----------------
def handle_statuses(statuses):
    """
    Update outgoing message status in DB by matching message_id.
    Expects list of status objects from WA webhook.
    """
    results = []
    if not VoterChatMessage:
        logger.error("VoterChatMessage model not found; cannot update statuses")
        return {"results": results}

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

                prev = chat.status
                chat.status = new_status

                update_fields = ["status"]
                if new_status == "read":
                    chat.read_at = timezone.now()
                    update_fields.append("read_at")

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
    Downloads media (if present) from WhatsApp and uploads to S3 immediately.
    Returns: {"saved": [...]}
    """
    saved = []
    if VoterChatMessage is None:
        logger.error("VoterChatMessage model not found; cannot save incoming messages.")
        return {"saved": saved}

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

            # # location
            # latitude = longitude = location_name = location_address = None
            # if msg_type == "location":
            #     loc = msg.get("location") or {}
            #     latitude = str(loc.get("latitude")) if loc.get("latitude") is not None else None
            #     longitude = str(loc.get("longitude")) if loc.get("longitude") is not None else None
            #     location_name = loc.get("name")
            #     location_address = loc.get("address")

            # media (image/video/audio/document)
            media_type = None
            media_id = None
            file_name = None
            media_url = None
            mime_from_payload = None
            for t in ("image", "video", "audio", "document"):
                if t == msg_type and t in msg:
                    media_type = t
                    payload = msg.get(t) or {}
                    media_id = payload.get("id")
                    file_name = payload.get("filename") or None
                    # sometimes payload contains mime info
                    mime_from_payload = payload.get("mime_type") or payload.get("mimetype") or None
                    break

            # context (reply-to)
            context_id = (msg.get("context") or {}).get("id")
            reply_to_db_id = _resolve_reply_to_db_id(context_id)

            # map 'from' to voter (if found)
            voter = _resolve_voter_by_whatsapp_from(raw_from)
            voter_id = voter.voter_list_id if voter else None
            sent_at = timezone.now()

            # If media present: download and upload to S3 (synchronously)
            if media_id:
                try:
                    # download_whatsapp_media returns (BytesIO, mime_type)
                    buf, detected_mime = download_whatsapp_media(media_id)

                    # coerce to BytesIO if needed
                    if not isinstance(buf, BytesIO):
                        if hasattr(buf, "iter_content"):
                            _buf = BytesIO()
                            for chunk in buf.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    _buf.write(chunk)
                            _buf.seek(0)
                            buf = _buf
                        else:
                            try:
                                buf = BytesIO(buf.read())
                                buf.seek(0)
                            except Exception:
                                # leave as-is; upload_to_s3 will attempt to handle
                                pass

                    mime_type = detected_mime or mime_from_payload or None
                    ext = _safe_extension_from_mime(mime_type, fallback=media_type or "bin")

                    # choose filename
                    if not file_name:
                        file_name = f"{media_id}.{ext}"

                    # build s3 filename (we pass a filename to upload_to_s3 so it uses it in returned key)
                    voter_part = str(voter_id) if voter_id else "unknown"
                    s3_folder = "voter_chat_media"
                    s3_key_filename = f"{wa_message_id or media_id}_{file_name}"
                    # upload (upload_to_s3 will create key using folder + uuid if you didn't want the exact name; we pass filename)
                    media_url = upload_to_s3(buf, folder=s3_folder, filename=s3_key_filename, acl= "public-read")

                    if not text_body:
                        text_body = f"{media_type} received"

                except Exception as e:
                    logger.exception("Failed download/upload media for %s: %s", media_id, e)
                    # preserve DB row even if upload fails (store media_id so you can retry)
                    media_url = None

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
                # "latitude": latitude,
                # "longitude": longitude,
                # "location_name": location_name,
                # "location_address": location_address,
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
