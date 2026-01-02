from rest_framework.throttling import SimpleRateThrottle

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
