import json
import re
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from typing import List, Tuple, Any, Dict, Optional

from application.models import VoterList
from .models import VoterChatMessage

url = settings.MESSAGE_URL
token = settings.ACCESS_TOKEN

# --- CONFIG: provider limit ---
PROVIDER_MAX_PER_SECOND = 50  # provider limit (messages / sec)
DEFAULT_CHUNK_SIZE = PROVIDER_MAX_PER_SECOND  # how many messages to send per second

# --- helpers ---
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
    Performs the HTTP call to provider and records a VoterChatMessage row.
    Returns a dict describing the result for the recipient (not an HttpResponse).
    """
    result: Dict[str, Any] = {"ok": False, "http_status": 0, "whatsapp_response": None, "error": None, "db_message_id": None, "db_status": None}

    # Validate sender fields
    if not sender_type:
        result.update({"error": "sender_type required", "http_status": 400})
        return result
    if sender_type in ("admin", "sub-admin") and not sender_id:
        result.update({"error": "sender_id required for admin/sub-admin", "http_status": 400})
        return result

    # Perform HTTP request to provider
    try:
        resp = requests.post(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=payload, timeout=http_timeout)
    except Exception as e:
        response_json = {"error": str(e)}
        resp_status = 0
        wa_message_id = None
    else:
        resp_status = getattr(resp, "status_code", 0)
        try:
            response_json = resp.json()
        except Exception:
            response_json = {"raw_text": getattr(resp, "text", "")}
        wa_message_id = None
        if resp_status and resp_status < 400:
            try:
                wa_message_id = response_json.get("messages", [])[0].get("id")
            except Exception:
                wa_message_id = None

    reply_to_db_id = _resolve_reply_to(reply_to_message_id)

    # Decide DB message id and status
    if wa_message_id:
        db_message_id = wa_message_id
        db_status = "sent" if resp_status < 400 else "failed"
    else:
        db_message_id = _make_fallback_local_id()
        db_status = "failed" if resp_status == 0 or resp_status >= 400 else "sent"

    # Build DB row kwargs
    instance_kwargs = {
        "message_id": db_message_id,
        "voter_id": voter.voter_list_id if getattr(voter, "voter_list_id", None) else None,
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
        result.update({"error": "Invalid sender_type", "http_status": 400})
        return result
    if reply_to_db_id:
        instance_kwargs["reply_to_id"] = reply_to_db_id

    # Save DB row (always attempt to save so UI can show message row)
    try:
        with transaction.atomic():
            chat_row = VoterChatMessage.objects.create(**instance_kwargs)
    except Exception as e:
        result.update({
            "error": f"DB error: {str(e)}",
            "http_status": 500,
            "whatsapp_response": response_json,
            "db_message_id": db_message_id,
            "db_status": db_status,
        })
        return result

    result.update({
        "ok": True if resp_status and resp_status < 400 else False,
        "http_status": resp_status,
        "whatsapp_response": response_json,
        "db_message_id": db_message_id,
        "db_status": db_status,
    })
    return result