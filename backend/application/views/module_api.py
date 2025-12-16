from django.http import JsonResponse
from ..models import (
    RoleModulePermission,
    Roles
)
from collections import defaultdict


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

    return JsonResponse({
        "status": True,
        "count": len(role_map),
        "data": list(role_map.values())
    })
