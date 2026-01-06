from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from twilio.rest import Client
import re
import time
from typing import Dict, Tuple
from django.http import JsonResponse
from rest_framework import status
from twilio.rest import Client
from .view_utils import validate_password
from ..models import VoterUserMaster

sid = os.getenv("TWILIO_ACCOUNT_SID")
token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(sid, token)
# print(sid, token, twilio_client)

def normalize_mobile(number):
    number = number.strip()
    if number.startswith("+"):
        return number
    return f"+91{number}"  # India default

E164_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")
 
# In-memory limiter: phone -> (window_start_epoch, count)
# NOTE: Not suitable for multi-instance production. Replace with Redis later.
_rate_store: Dict[str, Tuple[int, int]] = {}
 
def _require_e164(phone: str):
    if not phone or not E164_REGEX.match(phone):
        return False
    return True
 
def _rate_limit(phone: str, limit: int, window_seconds: int = 3600):
    now = int(time.time())
    window_start, count = _rate_store.get(phone, (now, 0))
    if now - window_start >= window_seconds:
        window_start, count = now, 0
    if count >= limit:
        return False
    _rate_store[phone] = (window_start, count + 1)
    return True
 
 
def _twilio_client() -> Client:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    # print(sid)
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    # print(token)
    if not sid or not token:
        raise ValueError("Twilio credentials missing")
    return Client(sid, token)
 
 
def _verify_service_sid() -> str:
    vsid = os.getenv("TWILIO_VERIFY_SERVICE_SID", "").strip()
    # print(vsid)
    if not vsid:
        raise ValueError("Verify service not configured")
    return vsid
 
 
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return JsonResponse({"status": "ok"}, status=200)

 
@api_view(["POST"])
@permission_classes([AllowAny])
def otp_start(request):
    
    data = request.data
    phone = (data.get("phone") or "").strip()
    channel = (data.get("channel") or "sms").strip().lower()
    # print(data)
    # phone = (request.data.get("phone") or "").strip()
    # channel = (request.data.get("channel") or "sms").strip().lower()
 
    if not _require_e164(phone):
        return JsonResponse(
            {"detail": "Phone must be in E.164 format, e.g. +919876543210"},
            status=status.HTTP_400_BAD_REQUEST
        )
 
    if channel not in ("sms", "call"):
        return JsonResponse(
            {"detail": "channel must be sms or call"},
            status=status.HTTP_400_BAD_REQUEST
        )
 
    try:
        vsid = _verify_service_sid()
        limit = int(os.getenv("RATE_LIMIT_PER_PHONE_PER_HOUR", "5"))
        if not _rate_limit(phone, limit=limit):
            return JsonResponse(
                {"detail": "Too many OTP requests. Try later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
 
        client = _twilio_client()
        res = client.verify.v2.services(vsid).verifications.create(
            to=phone,
            channel=channel
        )
 
        return JsonResponse({"status": True, "res-status": res.status, "sid": res.sid,"message": "OTP sent successfully"}, status=200)
 
    except Exception as e:
        # print("Twilio OTP error:", str(e))  #  ADD THIS
        return JsonResponse(
        {"status": False, "message": "Failed to start OTP", "error": str(e)},
        status=status.HTTP_400_BAD_REQUEST
    )
        
        
@api_view(["POST"])
@permission_classes([AllowAny])
def otp_verify(request):
    
    data = request.data
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()
 
    if not _require_e164(phone):
        return JsonResponse(
            {"detail": "Phone must be in E.164 format, e.g. +919876543210"},
            status=status.HTTP_400_BAD_REQUEST
        )
 
    if not code.isdigit():
        return JsonResponse(
            {"detail": "OTP code must be numeric"},
            status=status.HTTP_400_BAD_REQUEST
        )
 
    try:
        vsid = _verify_service_sid()
        client = _twilio_client()
 
        check = client.verify.v2.services(vsid).verification_checks.create(
            to=phone,
            code=code
        )
 
        if check.status == "approved":
            # In prod: issue JWT/session token here
            return JsonResponse({"status": True,"message":"OTP verified successfully"}, status=200)

        return JsonResponse({"status": False, "status": check.status}, status=200)

    except Exception:
        return JsonResponse({"status": False, "message": "Failed to verify OTP"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):

    data = request.data
    phone = (data.get("phone") or "").strip()
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    # ---------- BASIC CHECK ----------
    if not phone:
        return JsonResponse(
            {"detail": "Phone number is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ---------- FETCH USER ----------
    user = VoterUserMaster.objects.filter(mobile_no=phone[-10:]).first()

    if not user:
        return JsonResponse(
            {"detail": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # ---------- VALIDATE PASSWORD ----------
    try:
        validate_password(
            new_password=new_password,
            confirm_password=confirm_password,
            phone=phone,
            user=user            # correct user
        )
    except ValueError as e:
        return JsonResponse(
            {"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ---------- UPDATE PASSWORD ----------
    user.set_password(new_password)
    user.updated_at = timezone.now()
    user.save(update_fields=["password", "updated_at"])

    return JsonResponse(
        {"status": True, "message": "Password reset successful"},
        status=status.HTTP_200_OK
    )