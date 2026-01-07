from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from datetime import timedelta
import json
from .rate_limiter import get_client_ip,verify_captcha
from ..models import VoterUserMaster, VoterList,LoginAttempt
from logger import logger
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .view_utils import log_action_user


# ---------------- CONFIG ----------------
COMBO_CAPTCHA = 5
MOBILE_CAPTCHA = 5
IP_CAPTCHA = 10
IP_BLOCK = 20
BLOCK_MINUTES = 10
# ---------------------------------------


def get_attempt(key_type, key_value):
    attempt, _ = LoginAttempt.objects.get_or_create(
        key_type=key_type,
        key_value=key_value
    )
    return attempt


def reset_attempts(attempts):
    for a in attempts:
        a.failed_count = 0
        a.captcha_required = False
        a.blocked_until = None
        a.save()


@api_view(["POST"])
@permission_classes([AllowAny])
def id_validation(request):
    try:
        body = request.data
        logger.info("id_validation_api: ID validation request received")

        mobile_no = (body.get("mobile_no") or "").strip()
        password = (body.get("password") or "").strip()

        # -------- VALIDATIONS --------
        if not mobile_no:
            return Response(
                {"status": False, "message": "Mobile number is required"},
                status=400
            )

        if not password:
            return Response(
                {"status": False, "message": "Password is required"},
                status=400
            )

        ip = get_client_ip(request)
        now = timezone.now()

        # -------- LOAD ATTEMPTS --------
        ip_attempt = get_attempt("ip", ip)
        mobile_attempt = get_attempt("mobile", mobile_no)
        combo_attempt = get_attempt("ip_mobile", f"{ip}:{mobile_no}")

        attempts = [ip_attempt, mobile_attempt, combo_attempt]

        # -------- BLOCK CHECK --------
        for a in attempts:
            if a.blocked_until and a.blocked_until > now:
                log_action_user(
                        request=request,
                        user=None,  
                        action="LOGIN_BLOCKED",
                        module="AUTH",
                        status="FAILED",
                        metadata={
                            "mobile_no": mobile_no,
                            "blocked_until": str(a.blocked_until)
                        }
                    )

                return Response({
                    "status": False,
                    "message": "Too many attempts. Please try again later.",
                    "retry_after_seconds": int(
                        (a.blocked_until - now).total_seconds()
                    ),
                    "show_captcha": True
                }, status=429)

        # -------- CAPTCHA CHECK --------
        if any(a.captcha_required for a in attempts):
            captcha_id = body.get("captcha_id")
            captcha_value = body.get("captcha_value")

            if not captcha_id or not captcha_value:
                return Response({
                    "status": False,
                    "captcha_required": True,
                    "message": "Captcha required"
                }, status=403)

            if not verify_captcha(captcha_id, captcha_value):
                return Response({
                    "status": False,
                    "message": "Invalid captcha"
                }, status=403)

            # CAPTCHA SOLVED → RESET
            reset_attempts(attempts)


        # -------- FIND USER --------
        user = (
            VoterUserMaster.objects
            .filter(mobile_no=mobile_no)
            .select_related("role")
            .first()
        )

        # -------- PASSWORD CHECK --------
        if not user or not check_password(password, user.password):
            for a in attempts:
                a.failed_count += 1
                a.last_failed_at = now

            if combo_attempt.failed_count >= COMBO_CAPTCHA:
                combo_attempt.captcha_required = True

            if mobile_attempt.failed_count >= MOBILE_CAPTCHA:
                mobile_attempt.captcha_required = True

            if ip_attempt.failed_count >= IP_CAPTCHA:
                ip_attempt.captcha_required = True

            if ip_attempt.failed_count >= IP_BLOCK:
                ip_attempt.blocked_until = now + timedelta(minutes=BLOCK_MINUTES)

            for a in attempts:
                a.save()

            return Response({
                "status": False,
                "message": "Invalid mobile number or password",
                "captcha_required": any(a.captcha_required for a in attempts)
            }, status=401)

        # -------- SUCCESS --------
        reset_attempts(attempts)

        access_token = str(AccessToken.for_user(user))

        first = (user.first_name or "").capitalize()
        last = (user.last_name or "").capitalize()
        user_name = f"{first} {last}".strip()

        role_id = user.role.role_id if user.role else None
        role_name = user.role.role_name if user.role else None

        logger.info(f"id_validation_api: User {user.user_id} authenticated successfully")
        log_action_user(
            request=request,
            user=user,
            action="LOGIN_SUCCESS",
            module="AUTH",
            object_type="VoterUserMaster",
            object_id=user.user_id,
            metadata={
                "role_id": role_id,
                "role_name": role_name
            }
        )

        return Response({
            "status": True,
            "access_token": access_token,
            "token_type": "Bearer",
            "user_id": user.user_id,
            "assigned": VoterList.objects.filter(user_id=user.user_id).exists(),
            "user_name": user_name,
            "role_id": role_id,
            "role_name": role_name,
            "message": "Login successful"
        })

    except json.JSONDecodeError:
        return Response(
            {"status": False, "message": "Invalid JSON"},
            status=400
        )

    except Exception as e:
        logger.exception("id_validation_api error")
        return Response(
            {"status": False, "message": str(e)},
            status=500
        )
