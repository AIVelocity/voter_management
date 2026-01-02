from rest_framework.throttling import SimpleRateThrottle

class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        # Rate limit per mobile number OR IP
        mobile = request.data.get("mobile_no")
        if mobile:
            return self.cache_format % {
                "scope": self.scope,
                "ident": mobile
            }

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request)
        }
