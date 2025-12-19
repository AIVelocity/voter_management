import os
import mimetypes
import urllib.parse
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..utils.s3_integration import upload_to_s3
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

Upload_Url = getattr(settings, "UPLOAD_URL", None)
token = getattr(settings, "ACCESS_TOKEN", None)
ALLOWED_MEDIA_TYPES = {"image", "audio", "video", "document"}

# Limits (bytes)
MB = 1024 * 1024
LIMITS = {
    "image": 5 * MB,      # images: 5 MB
    "audio": 16 * MB,     # audio: 16 MB
    "video": 16 * MB,     # video: 16 MB
    "document": 100 * MB, # documents: 100 MB
}

# Allowed extensions and a small set of mime-types to validate (not exhaustive but practical)
ALLOWED_EXTENSIONS = {
    "image": {"jpeg", "jpg", "png"},
    "audio": {"aac", "amr", "mp3", "m4a", "ogg"},
    "video": {"mp4", "3gp", "3gpp"},
    "document": {"txt", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp"},
}

# Helpful mapping of common mime -> ext fallback
COMMON_MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "audio/aac": "aac",
    "audio/amr": "amr",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/ogg": "ogg",
    "video/mp4": "mp4",
    "video/3gpp": "3gp",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
}

def _bytes_human(n: int) -> str:
    if n >= MB:
        return f"{round(n / MB)} MB"
    return f"{n} bytes"

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
@csrf_exempt
@require_http_methods(["POST"])
def upload_media(request):
    """
    Upload media file to WhatsApp Cloud and optionally mirror to S3.
    Performs pre-upload validation (type + size) and returns friendly errors.
    """
    if not Upload_Url:
        return JsonResponse({"status": False, "message": "WHATSAPP upload URL not configured (UPLOAD_URL)"}, status=500)
    if not token:
        return JsonResponse({"status": False, "message": "ACCESS_TOKEN not configured in settings"}, status=500)

    upload_file = request.FILES.get("file")
    if not upload_file:
        return JsonResponse({"status": False, "message": "file (multipart) is required"}, status=400)

    media_type = request.POST.get("media_type", "image")
    if media_type not in ALLOWED_MEDIA_TYPES:
        return JsonResponse({"status": False, "message": f"Invalid media_type. Allowed: {', '.join(ALLOWED_MEDIA_TYPES)}"}, status=400)

    # Basic file metadata
    filename = getattr(upload_file, "name", "upload")
    size = getattr(upload_file, "size", None)
    content_type = getattr(upload_file, "content_type", None) or mimetypes.guess_type(filename)[0] or ""

    # Determine extension (normalize)
    _, ext = os.path.splitext(filename)
    ext = ext.lower().lstrip(".")  # e.g. "jpg"

    # If ext missing, try guessing from mime
    if not ext and content_type:
        ext = COMMON_MIME_TO_EXT.get(content_type.split(";")[0].strip(), "")

    # Validate size
    max_allowed = LIMITS.get(media_type)
    if size is None:
        # best-effort: try reading to determine size (but avoid full read for very large files)
        try:
            # .size should normally be available; fallback to len(read())
            cur = upload_file.read()
            size = len(cur)
            # rewind for later usage
            try:
                upload_file.seek(0)
            except Exception:
                pass
        except Exception:
            size = None

    if max_allowed and size is not None and size > max_allowed:
        return JsonResponse({
            "status": False,
            "message": f"File too large for {media_type}. Maximum allowed is {_bytes_human(max_allowed)}; uploaded file is {_bytes_human(size)}."
        }, status=400)

    # Validate extension / mime for media_type
    allowed_exts = ALLOWED_EXTENSIONS.get(media_type, set())
    # Normalise some common alias extensions
    if ext == "jpeg":
        ext_check = "jpg"
    else:
        ext_check = ext

    # For images we also allow "jpg" when ext is "jpeg"
    if not ext_check:
        # Unknown extension: check mime_type fallback
        mime_main = content_type.split(";")[0].strip().lower()
        ext_guess = COMMON_MIME_TO_EXT.get(mime_main, "")
        ext_check = ext_guess

    if ext_check and ext_check not in allowed_exts:
        return JsonResponse({
            "status": False,
            "message": f"Invalid file type for {media_type}. Allowed extensions: {', '.join(sorted(allowed_exts))}. Uploaded file extension: '{ext or '(none)'}'."
        }, status=400)

    # Special-case: images must be 8-bit RGB/RGBA — we can't check color depth server-side easily,
    # so we only check extension and size. If WhatsApp rejects, we return their error message below.

    # Rewind file pointer before sending
    try:
        upload_file.seek(0)
    except Exception:
        pass

    # Build multipart for WhatsApp
    files = {"file": (filename, upload_file.read(), content_type or "application/octet-stream")}
    data = {"type": media_type, "messaging_product": "whatsapp"}
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.post(Upload_Url, headers=headers, files=files, data=data, timeout=60)
    except requests.RequestException as exc:
        return JsonResponse({"status": False, "message": f"Upload request failed: {str(exc)}"}, status=500)

    # Parse response
    try:
        resp_json = resp.json()
    except Exception:
        resp_json = {"raw_text": getattr(resp, "text", "")}

    if resp.status_code >= 400:
        # Provide WhatsApp's error in natural language if possible
        err = resp_json.get("error") if isinstance(resp_json, dict) else None
        if isinstance(err, dict):
            details = err.get("error_data") or {}
            detail_msg = details.get("details") or err.get("message") or resp_json
            # For clarity, return small, user-friendly sentence
            user_msg = f"WhatsApp upload failed: {detail_msg}"
        else:
            user_msg = f"WhatsApp upload failed (HTTP {resp.status_code})"
        return JsonResponse({
            "status": False,
            "message": user_msg,
            "http_status": resp.status_code,
            "whatsapp_response": resp_json
        }, status=500)

    # Extract WA media id
    wa_media_id = None
    if isinstance(resp_json, dict):
        wa_media_id = resp_json.get("id")
        if not wa_media_id:
            media = resp_json.get("media")
            if isinstance(media, list) and media:
                wa_media_id = media[0].get("id")
        if not wa_media_id:
            messages = resp_json.get("messages")
            if isinstance(messages, list) and messages:
                wa_media_id = messages[0].get("id")

    if not wa_media_id:
        return JsonResponse({
            "status": False,
            "message": "Upload succeeded but response did not contain media id",
            "whatsapp_response": resp_json
        }, status=500)

    # Mirror to S3 (optional) — make sure to rewind first
    s3_error = None
    media_url = None
    upload_file_for_s3 = request.FILES.get("file")
    if upload_file_for_s3:
        try:
            try:
                upload_file_for_s3.seek(0)
            except Exception:
                pass
            media_url = upload_to_s3(upload_file_for_s3, filename)
        except Exception as e:
            media_url = None
            s3_error = str(e)

    if media_url:
        try:
            media_url = urllib.parse.urlsplit(media_url)._replace(query="").geturl()
        except Exception:
            pass

    resp_payload = {
        "status": True,
        "media_type": media_type,
        "media_id": wa_media_id,
        "media_url": media_url,
        "whatsapp_response": resp_json
    }
    if s3_error:
        resp_payload["s3_error"] = s3_error

    return JsonResponse(resp_payload, status=200)
