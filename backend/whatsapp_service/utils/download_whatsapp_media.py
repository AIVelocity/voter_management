# utils/download_whatsapp_media.py
import requests
from io import BytesIO
from django.conf import settings
import logging
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

def download_whatsapp_media(media_id: str, access_token: str | None = None, api_version: str = "v22.0"):
    """
    Download media from WhatsApp Graph API and return (BytesIO, mime_type)
    Raises RuntimeError on failure.
    """
    access_token = settings.ACCESS_TOKEN
    if not access_token:
        raise RuntimeError("WhatsApp access token is not configured in settings")

    # Step 1: get metadata (which contains the download URL)
    metadata_url = f"https://graph.facebook.com/{api_version}/{media_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        meta_resp = requests.get(metadata_url, headers=headers, timeout=15)
        meta_resp.raise_for_status()
    except RequestException as e:
        logger.exception("Failed to fetch media metadata for %s: %s", media_id, e)
        raise RuntimeError(f"Failed to get media metadata: {e}")

    meta_json = meta_resp.json()
    media_url = meta_json.get("url")
    mime_type = meta_json.get("mime_type") or meta_json.get("mimetype") or None

    if not media_url:
        logger.error("No media URL returned in metadata for media_id=%s metadata=%s", media_id, meta_json)
        raise RuntimeError("No media URL returned by WhatsApp metadata API")

    # Step 2: download the actual binary
    try:
        media_resp = requests.get(media_url, headers=headers, stream=True, timeout=30)
        media_resp.raise_for_status()
    except RequestException as e:
        logger.exception("Failed to download media binary for %s: %s", media_id, e)
        raise RuntimeError(f"Failed to download media: {e}")

    # Read into BytesIO
    buf = BytesIO()
    for chunk in media_resp.iter_content(chunk_size=1024 * 1024):
        if chunk:
            buf.write(chunk)
    buf.seek(0)

    return buf, mime_type
