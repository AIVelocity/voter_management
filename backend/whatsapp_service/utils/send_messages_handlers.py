import json
import re
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from typing import List, Tuple, Any, Dict, Optional
from datetime import timedelta
from application.models import VoterList
from ..models import VoterChatMessage
from logger import logger

url = settings.MESSAGE_URL
token = settings.ACCESS_TOKEN

logger.info("WhatsApp Service URL: %s", url)
logger.info("WhatsApp Service Token: %s", token[:5] + "..." if token else "None")
# --- CONFIG: provider limit ---
PROVIDER_MAX_PER_SECOND = 50  # provider limit (messages / sec)
DEFAULT_CHUNK_SIZE = PROVIDER_MAX_PER_SECOND  # how many messages to send per second


def parse_request_body(request) -> dict:
    """Return parsed JSON body (fallback to request.POST)."""
    try:
        return json.loads(request.body)
    except Exception:
        return request.POST.dict() if hasattr(request.POST, "dict") else request.POST
    

def _resolve_reply_to(reply_to_message_id: Optional[str]) -> Optional[int]:
    """
    Resolve a WA message_id -> VoterChatMessage PK (to link replies).
    Keep this to preserve reply threading.
    """
    if not reply_to_message_id:
        return None
    parent = VoterChatMessage.objects.filter(message_id=reply_to_message_id).first()
    return parent.id if parent else None

def _make_fallback_local_id() -> str:
    """Unique fallback local message id for DB when provider doesn't return one."""
    return f"local:{timezone.now().strftime('%Y%m%d%H%M%S%f')}:{uuid.uuid4().hex[:8]}"

def _chunked(iterable: List[Any], n: int):
    """Yield successive n-sized chunks from iterable."""
    for i in range(0, len(iterable), n):
        yield iterable[i:i + n]

def _clean_phone(raw: str) -> Optional[str]:
    """Remove non-digits and return string or None if empty."""
    if raw is None:
        return None
    s = re.sub(r"\D", "", str(raw))
    return s if s else None

def get_recipients_from_request(request) -> Tuple[List[Any], List[str]]:
    """
    Resolve request into a list of recipient objects (VoterList instances).
    Accepts:
      - voter_list_id (single) OR voter_list_ids (list)
    Returns:
      - recipients: list of VoterList instances (skips missing ids)
      - errors: list of non-fatal error messages to return to frontend
    """
    data = parse_request_body(request)
    recipients: List[Any] = []
    errors: List[str] = []

    voter_list_ids = data.get("voter_list_ids") or data.get("voter_list_id")
    if voter_list_ids is None:
        return [], ["voter_list_id or voter_list_ids required"]

    if isinstance(voter_list_ids, (str, int)):
        voter_list_ids = [voter_list_ids]
    # Normalize str ints
    voter_list_ids = list(map(lambda x: int(x) if isinstance(x, (int, str)) and str(x).isdigit() else x, voter_list_ids))
    for vid in voter_list_ids:
        try:
            v_obj = VoterList.objects.get(voter_list_id=vid)
            recipients.append(v_obj)
        except VoterList.DoesNotExist:
            errors.append(f"VoterList id {vid} not found - skipped")

    return recipients, errors


def is_within_reengagement_window(voter) -> bool:
    """
    Returns True if the voter has an incoming (non-admin) message within the last 24 hours.
    We treat any message whose sender is NOT 'admin' or 'sub-admin' as an incoming/customer message.
    Adjust the sender filtering if your sender values differ.
    """
    if not voter:
        return False

    # Find last non-admin message for this voter
    last_incoming = (
        VoterChatMessage.objects
        .filter(voter_id=getattr(voter, "voter_list_id", None))
        .filter(sender='voter')
        .order_by("-sent_at")
        .first()
    )
    if not last_incoming or not last_incoming.sent_at:
        return False

    return (timezone.now() - last_incoming.sent_at) <= timedelta(hours=24)


# --- core send function (returns dict for each recipient) ---
def send_whatapps_request(payload: dict,
                          voter: Any,
                          message: Optional[str] = None,
                          message_type: str = "text",
                          sender_type: Optional[str] = None,
                          sender_id: Optional[int] = None,
                          media_id: Optional[str] = None,
                          media_url: Optional[str] = None,
                          reply_to_message_id: Optional[str] = None,
                          http_timeout: int = 30) -> Dict[str, Any]:
    """
    CLEAN + FINAL VERSION
    ---------------------
    - All API-outgoing messages (Admin, subAdmin, user) are saved as sender='user'
    - sender_user_id always = sender_id
    - sender_role_id / sender_role resolved from VoterUserMaster.role FK
    - No duplicate logic
    """

    result = {
        "ok": False,
        "http_status": 0,
        "whatsapp_response": None,
        "error": None,
        "db_message_id": None,
        "db_status": None
    }
    if sender_type not in ("Admin", "subAdmin", "user"):
        result.update({"error": "Invalid sender_type", "http_status": 400})
        return result

    if not sender_id:
        result.update({"error": "sender_id required", "http_status": 400})
        return result

    normalized_sender = "user"
    sender_user_obj = None
    sender_role_id_val = None
    sender_role_name = None

    try:
        from django.apps import apps
        VoterUserMaster = apps.get_model("application", "VoterUserMaster")

        sender_user_obj = VoterUserMaster.objects.filter(pk=sender_id).first()
        if sender_user_obj:
            role_obj = getattr(sender_user_obj, "role", None)
            if role_obj:
                sender_role_id_val = getattr(role_obj, "role_id", None)
                sender_role_name = getattr(role_obj, "role_name", None)

    except Exception:
        pass  # keep role fields empty if resolution fails

    if message_type != "template" and not is_within_reengagement_window(voter):
        db_id = _make_fallback_local_id()
        reply_to_db = _resolve_reply_to(reply_to_message_id)

        instance_kwargs = {
            "message_id": db_id,
            "voter_id": getattr(voter, "voter_list_id", None),
            "sender": normalized_sender,
            "status": "failed",
            "message": message,
            "type": message_type,
            "media_id": media_id,
            "media_url": media_url,
            "sent_at": timezone.now(),
            "sender_user_id": sender_id,
            "sender_role_id": sender_role_id_val,
            "sender_role": sender_role_name,
        }

        if reply_to_db:
            instance_kwargs["reply_to_id"] = reply_to_db

        VoterChatMessage.objects.create(**instance_kwargs)

        result.update({
            "error": "reengagement_window_closed",
            "http_status": 400,
            "db_message_id": db_id,
            "db_status": "failed",
        })
        return result

    response_json = None
    resp_status = 0
    wa_message_id = None

    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=http_timeout,
        )
        resp_status = resp.status_code
        try:
            response_json = resp.json()
        except:
            response_json = {"raw": resp.text}

        # Extract WA message ID
        if resp_status < 400:
            if "messages" in response_json:
                wa_message_id = response_json["messages"][0].get("id")
            if not wa_message_id:
                wa_message_id = response_json.get("id")

    except Exception as e:
        response_json = {"error": str(e)}

    # Fallback message_id
    db_message_id = wa_message_id or _make_fallback_local_id()
    db_status = "sent" if resp_status and resp_status < 400 else "failed"

    reply_to_db = _resolve_reply_to(reply_to_message_id)

    instance_kwargs = {
        "message_id": db_message_id,
        "voter_id": getattr(voter, "voter_list_id", None),
        "sender": normalized_sender,
        "status": db_status,
        "message": message,
        "type": message_type,
        "media_id": media_id,
        "media_url": media_url,
        "sent_at": timezone.now(),
        "sender_user_id": sender_id,
        "sender_role_id": sender_role_id_val,
        "sender_role": sender_role_name,
    }

    if reply_to_db:
        instance_kwargs["reply_to_id"] = reply_to_db

    VoterChatMessage.objects.create(**instance_kwargs)

    result.update({
        "ok": resp_status < 400,
        "http_status": resp_status,
        "whatsapp_response": response_json,
        "db_message_id": db_message_id,
        "db_status": db_status,
    })
    return result
