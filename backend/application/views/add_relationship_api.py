from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import IntegrityError
from ..models import VoterRelationshipDetails
import json

def parse_json(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return None

REVERSE_MAP = {
    "father": "child",
    "mother": "child",
    "child": "parent",
    "parent": "child",
    "husband": "wife",
    "wife": "husband",
    "sibling": "sibling",
    "spouse": "spouse"
}

@csrf_exempt
def add_relation(request):

    try:
        body = parse_json(request)
        if not body:
            return JsonResponse(
                {"status": False, "message": "Invalid JSON body"},
                status=400
            )

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        if not voter_id or not related_id or not relation:
            return JsonResponse(
                {"status": False, "message": "Missing parameters"},
                status=400
            )

        relation = relation.lower()

        # Conflict check
        if VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id
        ).exists():
            return JsonResponse(
                {
                    "status": False,
                    "message": "Relation already exists between voters"
                },
                status=409
            )

        reverse = REVERSE_MAP.get(relation)

        if not reverse:
            return JsonResponse(
                {"status": False, "message": "Invalid relation"},
                status=400
            )

        # Create primary relation
        VoterRelationshipDetails.objects.get_or_create(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation,
        )

        # Create reverse relation
        VoterRelationshipDetails.objects.get_or_create(
            voter_id=related_id,
            related_voter_id=voter_id,
            relation_with_voter=reverse,
        )

        return JsonResponse({
            "status": True,
            "message": "Relation added successfully"
        })

    except IntegrityError:
        return JsonResponse(
            {"status": False, "message": "Duplicate or FK violation"},
            status=400
        )

    except Exception as e:
        print("ADD RELATION ERROR:", str(e))
        return JsonResponse(
            {"status": False, "message": "Server error"},
            status=500
        )


@csrf_exempt
def remove_relation(request):

    try:
        body = parse_json(request)
        if not body:
            return JsonResponse(
                {"status": False, "message":"Invalid JSON body"},
                status=400
            )

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        if not voter_id or not related_id or not relation:
            return JsonResponse(
                {"status": False, "message":"Missing parameters"},
                status=400
            )

        relation = relation.lower()

        VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation
        ).delete()

        reverse = REVERSE_MAP.get(relation)

        if reverse:
            VoterRelationshipDetails.objects.filter(
                voter_id=related_id,
                related_voter_id=voter_id,
                relation_with_voter=reverse
            ).delete()

        return JsonResponse({"status": True,"message":"Deleted successfully"})

    except Exception as e:
        print("REMOVE RELATION ERROR:", str(e))
        return JsonResponse(
            {"status": False, "message": "Server error"},
            status=500
        )
