import uuid
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .view_utils import generate_captcha

CAPTCHA_TTL = 300  # 5 minutes

@api_view(["GET"])
def get_captcha(request):
    text, image = generate_captcha()
    captcha_id = str(uuid.uuid4())

    cache.set(f"captcha:{captcha_id}", text, CAPTCHA_TTL)

    return Response({
        "status": True,
        "captcha_id": captcha_id,
        "captcha_image": image
    })
