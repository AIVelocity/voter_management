
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from ..models import VoterUserMaster, Roles,VoterList
import json
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_volunteers(request):

    volunteers = (
        VoterUserMaster.objects
        .filter(role__role_name="Volunteer")
        .values(
            "user_id",
            "first_name",
            "last_name",
            "mobile_no",
            "created_date"
        )
        .order_by("created_date")
    )

    return Response({
        "status": True,
        "count": volunteers.count(),
        "volunteers": list(volunteers)
    })

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def single_volunteer(request, user_id):

    if request.method != "GET":
        return Response({
            "status": False,
            "message": "GET method required"
        }, status=405)
        
    # print("AUTH HEADER:", request.headers.get("Authorization"))

    auth_header = request.headers.get("Authorization")
    logged_in_user_id = None

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = AccessToken(auth_header.split(" ")[1])
            logged_in_user_id = token["user_id"]
        except Exception:
            return Response(
                {"status": False, "message": "Invalid or expired token"},
                status=401
            )

    if not logged_in_user_id:
        return Response(
            {"status": False, "message": "Unauthorized"},
            status=401
        )

    try:
        user = (
            VoterUserMaster.objects
            .select_related("role")
            .filter(user_id=user_id)
            .first()
        )

        if not user:
            return Response({
                "status": False,
                "message": "User not found"
            }, status=404)

        response = {
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "mobile_no": user.mobile_no,
            "role_id": user.role.role_id if user.role else None,
            "role_name": user.role.role_name if user.role else None,
            "created_date": user.created_date,
        }

        # ---------------- ROLE BASED DATA ----------------

        # SUPER ADMIN
        if user.role and user.role.role_name == "SuperAdmin":
            response["ward_no"] = 37
            response["admin_count"] = (
                VoterUserMaster.objects
                .filter(role__role_name="Admin")
                .count()
            )
            response["volunteer_count"] = (
                VoterUserMaster.objects
                .filter(role__role_name="Volunteer")
                .count()
            )
            response["total_member_count"] = response["admin_count"] + response["volunteer_count"]
        # ADMIN
        elif user.role and user.role.role_name == "Admin":
            response["ward_no"] =37
            response["volunteer_count"] = (
                VoterUserMaster.objects
                .filter(
                    role__role_name="Volunteer",
                    # ward_no=user.ward_no
                )
                .count()
            )

        # VOLUNTEER
        elif user.role and user.role.role_name == "Volunteer":
            response["ward_no"]=37
            response["allocated_voter_count"] = (
                VoterList.objects
                .filter(user=user)
                .count()
            )

        return Response({
            "status": True,
            "data": response
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)




ROLE_LEVELS = {
    "SuperAdmin": 1,
    "Admin": 2,
    "Volunteer": 3,
}

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def promote_user(request):

    if request.method != "POST":
        return Response({
            "status": False,
            "message": "POST method required"
        }, status=405)

    try:
        # auth_header = request.headers.get("Authorization")
        body = request.data

        target_user_id = body.get("target_user_id")
        new_role_name = body.get("new_role")

        if not target_user_id or not new_role_name:
            return Response({
                "status": False,
                "message": "target_user_id and new_role are required"
            }, status=400)
        try:
            target_user = VoterUserMaster.objects.get(user_id=target_user_id)
        except VoterUserMaster.DoesNotExist:
            return Response({
                "status": False,
                "message": "Target user not found"
            }, status=404)

        if new_role_name not in ROLE_LEVELS:
            return Response({
                "status": False,
                "message": "Invalid target role"
            }, status=400)

        new_role = Roles.objects.get(role_name=new_role_name)

        with transaction.atomic():
            target_user.role = new_role
            # target_user.updated_by = logged_in_user.user_id
            target_user.updated_date = timezone.now()
            target_user.save()

        return Response({
            "status": True,
            "message": f"User promoted to {new_role_name}",
            "user_id": target_user.user_id
        })

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=500)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):

    # ---------------- AUTH ----------------
    auth_header = request.headers.get("Authorization")
    logged_in_user_id = None

    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = AccessToken(auth_header.split(" ")[1])
            logged_in_user_id = token["user_id"]
        except Exception:
            return Response(
                {"status": False, "message": "Invalid or expired token"},
                status=401
            )

    if not logged_in_user_id:
        return Response(
            {"status": False, "message": "Unauthorized"},
            status=401
        )
    # ---------------- DELETE USER ----------------
    try:
        target_user = VoterUserMaster.objects.get(user_id=user_id)
        target_user.delete()

        return Response({
            "status": True,
            "message": "User deleted successfully"
        })

    except VoterUserMaster.DoesNotExist:
        return Response(
            {"status": False, "message": "User not found"},
            status=404
        )

