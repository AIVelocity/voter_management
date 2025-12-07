from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import IntegrityError
from psycopg.errors import ForeignKeyViolation
from ..models import VoterRelationshipDetails
import json


REVERSE_MAP = {
    "father": "child",
    "mother": "child",
    "child": "parent",
    "parent": "child",
    "husband": "wife",
    "wife": "husband",
    "sibling": "sibling",
}


@csrf_exempt
def add_relation(request):

    try:

        body = json.loads(request.body)
        if not body:
            return JsonResponse({"status": False, "message":"Invalid JSON"}, status=400)

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        # -------- VALIDATION --------
        if not voter_id or not related_id or not relation:
            return JsonResponse({
                "status": False,
                "message":"voter_list_id, related_voter_list_id & relation required"
            }, status=400)

        relation = relation.lower()

        if relation not in REVERSE_MAP:
            return JsonResponse({
                "status": False,
                "message": f"Invalid relation '{relation}'"
            }, status=400)

        if voter_id == related_id:
            return JsonResponse({
                "status": False,
                "message": "Self relationship not allowed"
            }, status=400)

        # ---------- CONFLICT CHECK ----------
        conflict = VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id
        ).exists()

        if conflict:
            return JsonResponse({
                "status": False,
                "message":
                    "This voter already has a relationship with this person. "
                    "Remove the existing relation first."
            }, status=409)

        # ---------- SINGLE ROLE CHECK ----------
        SINGLE_RELATIONS = ["father", "mother", "husband", "wife"]

        if relation in SINGLE_RELATIONS:
            if VoterRelationshipDetails.objects.filter(
                voter_id=voter_id,
                relation_with_voter=relation
            ).exists():

                return JsonResponse({
                    "status": False,
                    "message": f"{relation.title()} already exists."
                }, status=409)

        # ---------- SAVE PRIMARY ----------
        VoterRelationshipDetails.objects.get_or_create(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation
        )

        # ---------- SAVE REVERSE ----------
        reverse_relation = REVERSE_MAP.get(relation)
        if reverse_relation:
            VoterRelationshipDetails.objects.get_or_create(
                voter_id=related_id,
                related_voter_id=voter_id,
                relation_with_voter=reverse_relation
            )

        return JsonResponse({
            "status": True,
            "message": "Relation added successfully"
        })

    except IntegrityError:
        return JsonResponse({"status": False, "message":"Duplicate relationship"}, status=409)

    except Exception as e:
        return JsonResponse({"status": False, "message":str(e)}, status=500)



# REMOVE RELATION
@csrf_exempt
def remove_relation(request):

    try:

        body = json.loads(request.body)

        if not body:
            return JsonResponse({
                "status": False,
                "message": "Invalid JSON body"
            }, status=400)

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        # ------- VALIDATION -------
        if not voter_id or not related_id or not relation:
            return JsonResponse({
                "status": False,
                "message": "voter_list_id, related_voter_list_id and relation are required"
            }, status=400)

        relation = relation.lower()

        if relation not in REVERSE_MAP:
            return JsonResponse({
                "status": False,
                "message": f"Invalid relation '{relation}'"
            }, status=400)

        # ------- DELETE PRIMARY -------
        deleted_main, _ = VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation
        ).delete()

        # ------- DELETE REVERSE -------
        reverse_relation = REVERSE_MAP.get(relation)

        deleted_reverse = 0
        if reverse_relation:
            deleted_reverse, _ = VoterRelationshipDetails.objects.filter(
                voter_id=related_id,
                related_voter_id=voter_id,
                relation_with_voter=reverse_relation
            ).delete()

        if not deleted_main and not deleted_reverse:
            return JsonResponse({
                "status": False,
                "message": "Relationship not found"
            }, status=404)

        return JsonResponse({
            "status": True,
            "message": "Relationship removed successfully"
        })

    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": f"Unexpected error: {str(e)}"
        }, status=500)
