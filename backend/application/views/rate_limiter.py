from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import Throttled
from django.conf import settings
from django.core.cache import cache

from rest_framework.exceptions import PermissionDenied
from ..models import BlockedIP
from logger import logger

# def get_client_ip(request):
#     """
#     Normal IP detection + hard block if X-Forwarded-For is present
#     """

#     xff = request.META.get("HTTP_X_FORWARDED_FOR")

#     if xff:
#         ip = xff.split(",")[0].strip()

#         # BlockedIP.objects.get_or_create(
#         #     ip_address=ip,
#         #     defaults={"reason": "X-Forwarded-For detected"}
#         # )

#         logger.warning(f"Blocked IP due to X-Forwarded-For: {ip}")

#         raise PermissionDenied("Your IP has been blocked")

#     # EXISTING NORMAL LOGIC (unchanged)
#     ip = request.META.get("REMOTE_ADDR")

#     return ip


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    # print("-------------->>>xff :",xff)
    if xff:
        return xff.split(",")[0].strip()
    # print("--------IP--->>:",request.META.get("REMOTE_ADDR"))
    return request.META.get("REMOTE_ADDR")

def verify_captcha(captcha_id, user_value):
    real = cache.get(f"captcha:{captcha_id}")

    if not real:
        return False

    cache.delete(f"captcha:{captcha_id}")  # one-time use
    return real.lower() == user_value.lower()

