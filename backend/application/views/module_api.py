
from collections import defaultdict
from django.db import transaction
from ..models import (
    Roles,
    VoterModuleMaster,
    RoleModulePermission
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_roles_permissions(request):

    permissions_qs = (
        RoleModulePermission.objects
        .select_related("role", "module")
        .order_by("role__role_id", "module__module_name")
    )

    role_map = defaultdict(lambda: {
        "role_id": None,
        "role_name": None,
        "permissions": []
    })

    for rp in permissions_qs:
        role_id = rp.role.role_id

        role_map[role_id]["role_id"] = role_id
        role_map[role_id]["role_name"] = rp.role.role_name

        role_map[role_id]["permissions"].append({
            "module": rp.module.module_name,
            "view": rp.can_view,
            "add": rp.can_add,
            "edit": rp.can_edit,
            "delete": rp.can_delete
        })

    return Response({
        "status": True,
        "count": len(role_map),
        "data": list(role_map.values())
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_roles_permissions(request):


    role_id = request.query_params.get("role_id")

    qs = (
        RoleModulePermission.objects
        .select_related("role", "module")
    )

    if role_id:
        qs = qs.filter(role__role_id=role_id)

    qs = qs.order_by("module__module_name")

    if not qs.exists():
        return Response({
            "status": False,
            "message": "No permissions found for this role"
        }, status=404)

    role = qs.first().role

    data = {
        "role_id": role.role_id,
        "role_name": role.role_name,
        "permissions": []
    }

    for rp in qs:
        data["permissions"].append({
            "module": rp.module.module_name,
            "view": rp.can_view,
            "add": rp.can_add,
            "edit": rp.can_edit,
            "delete": rp.can_delete
        })

    return Response({
        "status": True,
        "data": data
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_update_permissions(request):

    if request.method != "POST":
        return Response(
            {"status": False, "message": "POST method required"},
            status=405
        )

    try:
        body = request.data
        data = body.get("data")

        if not data or not isinstance(data, list):
            return Response(
                {"status": False, "message": "data must be a list"},
                status=400
            )

        roles = {
            r.role_name: r
            for r in Roles.objects.filter(
                role_name__in=[item["role"] for item in data]
            )
        }

        modules = {
            m.module_name: m
            for m in VoterModuleMaster.objects.all()
        }

        updated_rows = 0

        with transaction.atomic():
            for item in data:
                role_name = item.get("role")
                permissions = item.get("permissions", [])

                role = roles.get(role_name)
                if not role:
                    continue

                for perm in permissions:
                    module = modules.get(perm.get("module"))
                    if not module:
                        continue

                    updated = RoleModulePermission.objects.filter(
                        role=role,
                        module=module
                    ).update(
                        can_view=perm.get("view", False),
                        can_add=perm.get("add", False),
                        can_edit=perm.get("edit", False),
                        can_delete=perm.get("delete", False)
                    )

                    updated_rows += updated

        return Response({
            "status": True,
            "message": "Permissions updated successfully",
            "roles_processed": len(data),
            "rows_updated": updated_rows
        })

    except Exception as e:
        return Response(
            {"status": False, "error": str(e)},
            status=500
        )
