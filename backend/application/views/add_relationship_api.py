from django.db import IntegrityError
from ..models import VoterRelationshipDetails
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_relation(request):

    try:
        body = request.data
        if not body:
            return Response(
                {"status": False, "message": "Invalid JSON body"},
                status=400
            )

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        if not voter_id or not related_id or not relation:
            return Response(
                {"status": False, "message": "Missing parameters"},
                status=400
            )

        relation = relation.lower()

        # Conflict check
        if VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id
        ).exists():
            return Response(
                {
                    "status": False,
                    "message": "Relation already exists between voters"
                },
                status=409
            )

        reverse = REVERSE_MAP.get(relation)

        if not reverse:
            return Response(
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

        return Response({
            "status": True,
            "message": "Relation added successfully"
        })

    except IntegrityError:
        return Response(
            {"status": False, "message": "Duplicate or FK violation"},
            status=400
        )

    except Exception as e:
        print("ADD RELATION ERROR:", str(e))
        return Response(
            {"status": False, "message": "Server error"},
            status=500
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_relation(request):

    try:
        body = request.data
        if not body:
            return Response(
                {"status": False, "message":"Invalid JSON body"},
                status=400
            )

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        if not voter_id or not related_id or not relation:
            return Response(
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

        return Response({"status": True,"message":"Deleted successfully"})

    except Exception as e:
        print("REMOVE RELATION ERROR:", str(e))
        return Response(
            {"status": False, "message": "Server error"},
            status=500
        )
