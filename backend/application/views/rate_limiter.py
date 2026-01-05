from rest_framework.throttling import SimpleRateThrottle
from django.conf import settings

import requests
class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        ip = self.get_ident(request)
        mobile = request.data.get("mobile_no")

        if not mobile:
            ident = ip
        else:
            ident = f"{ip}:{mobile}"

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident
        }

def verify_captcha(token):
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": settings.RECAPTCHA_SECRET_KEY,
            "response": token
        },
        timeout=5
    )
    return response.json().get("success", False)
