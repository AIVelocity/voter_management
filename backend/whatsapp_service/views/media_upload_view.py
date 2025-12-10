import mimetypes
import urllib.parse
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..utils.s3_integration import upload_to_s3

Upload_Url = settings.UPLOAD_URL
token = settings.ACCESS_TOKEN
ALLOWED_MEDIA_TYPES = {"image", "audio", "video", "document"}


@csrf_exempt
@require_http_methods(["POST"])
def upload_media(request):
    """
    Upload media file to WhatsApp Cloud and optionally mirror to S3.
    Expects multipart/form-data with:
      - file: file to upload
      - media_type: one of image/audio/video/document (optional, defaults to 'image')
    Returns JSON:
      {
        "status": True,
        "media_type": "image",
        "media_id": "<whatsapp_media_id>",
        "media_url": "<s3_or_none>",
        "whatsapp_response": {...}
      }
    """
    # Basic validations
    if not Upload_Url:
        return JsonResponse({"status": False, "message": "WHATSAPP upload URL not configured (WHATSAPP_UPLOAD_URL/UPLOAD_URL)"}, status=500)

    
    if not token:
        return JsonResponse({"status": False, "message": "ACCESS_TOKEN not configured in settings"}, status=500)

    # Get file
    upload_file = request.FILES.get("file")
    if not upload_file:
        return JsonResponse({"status": False, "message": "file (multipart) is required"}, status=400)

    media_type = request.POST.get("media_type", "image")
    if media_type not in ALLOWED_MEDIA_TYPES:
        return JsonResponse({"status": False, "message": f"Invalid media_type. Allowed: {', '.join(ALLOWED_MEDIA_TYPES)}"}, status=400)

    # Guess mime type
    filename = getattr(upload_file, "name", "upload")
    mime_type = mimetypes.guess_type(filename)[0] or upload_file.content_type or "application/octet-stream"

    # Build multipart payload for WhatsApp Cloud API
    files = {
        "file": (filename, upload_file.read(), mime_type),
    }
    # Some providers accept the type as part of multipart non-file fields
    data = {
        "type": media_type,
        "messaging_product": "whatsapp"
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        # send to WhatsApp upload endpoint
        resp = requests.post(Upload_Url, headers=headers, files=files, data=data, timeout=60)
    except requests.RequestException as exc:
        return JsonResponse({"status": False, "message": f"Upload request failed: {str(exc)}"}, status=500)

    # Parse response
    try:
        resp_json = resp.json()
    except Exception:
        resp_json = {"raw_text": getattr(resp, "text", "")}

    if resp.status_code >= 400:
        return JsonResponse({
            "status": False,
            "message": "WhatsApp upload failed",
            "http_status": resp.status_code,
            "whatsapp_response": resp_json
        }, status=500)

    # Typical Cloud API returns {"id": "<media_id>"} but vary by provider — try safe reads
    wa_media_id = None
    if isinstance(resp_json, dict):
        # direct id
        wa_media_id = resp_json.get("id")

        # media: [ { "id": ... } ]
        if not wa_media_id:
            media = resp_json.get("media")
            if isinstance(media, list) and len(media) > 0:
                wa_media_id = media[0].get("id")

        # messages: [ { "id": ... } ] (some endpoints return messages array)
        if not wa_media_id:
            messages = resp_json.get("messages")
            if isinstance(messages, list) and len(messages) > 0:
                wa_media_id = messages[0].get("id")
    if not wa_media_id:
        # If we can't find ID, still return entire whatsapp response
        return JsonResponse({
            "status": False,
            "message": "Upload succeeded but response did not contain media id",
            "whatsapp_response": resp_json
        }, status=500)

    # Optionally mirror uploaded file to S3 (so you keep a public/archival copy). This helper returns a URL or None.
    try:
        # rewind file pointer to start (we read above). If you prefer to upload original file object, use upload_file
        # We will upload using the original InMemoryUploadedFile or TemporaryUploadedFile; ensure pointer is reset.
        # Here we'll attempt to get original file back from request.FILES for S3 helper.
        upload_file_for_s3 = request.FILES.get("file")
        media_url = None
        try:
            media_url = upload_to_s3(upload_file_for_s3, filename)
        except Exception as e:
            # don't fail the whole API if S3 upload fails; include error in response
            media_url = None
            s3_error = str(e)
        else:
            s3_error = None
    except Exception as e:
        media_url = None
        s3_error = str(e)

    # strip query params from media_url if present
    if media_url:
        media_url = urllib.parse.urlsplit(media_url)._replace(query="").geturl()

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
