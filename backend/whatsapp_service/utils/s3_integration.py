# utils/s3_integration.py
import boto3
import mimetypes
import uuid
from io import BytesIO
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Lazy-create client for thread-safety in Django workers
def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_S3_REGION_NAME", None),
    )

BUCKET = getattr(settings, "AWS_S3_BUCKET_NAME", None)
REGION = getattr(settings, "AWS_S3_REGION_NAME", "")


def upload_to_s3(file_obj, folder: str = "chat_media", filename: str | None = None, acl: str = "public-read") -> str:
    """
    Uploads a file-like object (BytesIO, Django UploadedFile, or requests.Response wrapped into BytesIO)
    to S3 and returns a constructed URL.

    - file_obj: BytesIO or file-like (must support .read())
    - folder: top-level folder name (will create folder/<uuid>.ext)
    - filename: optional suggestion for filename (used in returned URL key name)
    - acl: "public-read" or "private"
    """
    if not BUCKET:
        raise RuntimeError("AWS_S3_BUCKET_NAME is not configured in settings")

    # Try to determine a base filename
    original_name = None
    try:
        original_name = getattr(file_obj, "name", None)
    except Exception:
        original_name = None

    if filename:
        original_name = filename

    if not original_name:
        # try to guess extension from content-type header if present
        content_type = None
        if hasattr(file_obj, "headers") and isinstance(getattr(file_obj, "headers"), dict):
            content_type = file_obj.headers.get("Content-Type") or file_obj.headers.get("content-type")
        ext = ""
        if content_type:
            ext = mimetypes.guess_extension(content_type) or ""
        original_name = f"{uuid.uuid4().hex}.{ext[1:] if ext.startswith('.') else (ext or 'bin')}"

    # build a unique key
    extension = original_name.split(".")[-1] if "." in original_name else ""
    unique_name = f"{uuid.uuid4().hex}.{extension}" if extension else uuid.uuid4().hex
    # NOTE: folder should be like 'chat_media' (no leading/trailing slash)
    key = f"{folder.rstrip('/')}/{unique_name}"

    # Prepare file-like for boto3
    # if it's a requests.Response-like with iter_content, convert to BytesIO
    file_like = None
    try:
        if hasattr(file_obj, "iter_content") and callable(getattr(file_obj, "iter_content")):
            buf = BytesIO()
            for chunk in file_obj.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    buf.write(chunk)
            buf.seek(0)
            file_like = buf
        else:
            # ensure seek to 0 if possible
            try:
                file_obj.seek(0)
            except Exception:
                pass
            file_like = file_obj
    except Exception as e:
        logger.exception("Failed to coerce file_obj to file-like: %s", e)
        raise

    # Determine mime_type
    mime_type = getattr(file_obj, "content_type", None) or None
    if not mime_type and hasattr(file_obj, "headers") and isinstance(getattr(file_obj, "headers"), dict):
        mime_type = file_obj.headers.get("Content-Type") or file_obj.headers.get("content-type")
    if not mime_type:
        mime_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"

    # Seek to beginning
    try:
        file_like.seek(0)
    except Exception:
        pass

    s3 = get_s3_client()
    extra_args = {"ContentType": mime_type, "ContentDisposition": "inline"}
    if acl:
        extra_args["ACL"] = acl

    s3.upload_fileobj(Fileobj=file_like, Bucket=BUCKET, Key=key, ExtraArgs=extra_args)

    base_override = getattr(settings, "AWS_S3_BASE_URL", "").strip()
    if base_override:
        return f"{base_override.rstrip('/')}/{key}"
    if REGION and REGION != "us-east-1":
        return f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{key}"
    else:
        return f"https://{BUCKET}.s3.amazonaws.com/{key}"
