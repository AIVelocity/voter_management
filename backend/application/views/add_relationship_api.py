from django.db import IntegrityError
from ..models import VoterRelationshipDetails,VoterList, VoterUserMaster
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from logger import logger

from .view_utils import log_user_update
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
        logger.info("add_relationship_api: Add relation request received")
        body = request.data

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        if not voter_id or not related_id or not relation:
            return Response(
                {"status": False, "message": "Missing parameters"},
                status=400
            )

        relation = relation.lower()
        reverse = REVERSE_MAP.get(relation)

        if not reverse:
            return Response(
                {"status": False, "message": "Invalid relation"},
                status=400
            )

        # -------- FETCH NAMES (ONCE) --------
        voter = VoterList.objects.filter(
            voter_list_id=voter_id
        ).only("voter_name_eng").first()

        related_voter = VoterList.objects.filter(
            voter_list_id=related_id
        ).only("voter_name_eng").first()

        voter_name = voter.voter_name_eng if voter else None
        related_voter_name = related_voter.voter_name_eng if related_voter else None

        # -------- DUPLICATE CHECK --------
        if VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation
        ).exists():
            return Response(
                {"status": False, "message": "Relation already exists"},
                status=409
            )

        logger.info(f"Adding relation: {voter_name} ({voter_id}) - {relation} -> {related_voter_name} ({related_id})")
        # -------- CREATE RELATIONS --------
        VoterRelationshipDetails.objects.create(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation,
        )
        
        VoterRelationshipDetails.objects.create(
            voter_id=related_id,
            related_voter_id=voter_id,
            relation_with_voter=reverse,
        )


        # -------- LOG (NAMES ONLY) --------
        new_data = {
            "voter_name": voter_name,
            "related_voter_name": related_voter_name,
            "relation": relation,
            "reverse_relation": reverse,
        }

        log_user_update(
            user=request.user,
            action="ADD_RELATION",
            voter_list_id=voter_id,
            description="Added voter relationship",
            old_data=None,
            new_data=new_data,
        )
        logger.info("Relation added successfully")
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
        # print("ADD RELATION ERROR:", str(e))
        return Response(
            {"status": False, "message": "Server error"},
            status=500
        )
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_relation(request):

    try:
        body = request.data

        voter_id = body.get("voter_list_id")
        related_id = body.get("related_voter_list_id")
        relation = body.get("relation")

        if not voter_id or not related_id or not relation:
            return Response(
                {"status": False, "message": "Missing parameters"},
                status=400
            )

        relation = relation.lower()
        reverse = REVERSE_MAP.get(relation)

        # -------- FETCH EXISTING --------
        existing = VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation
        ).first()

        if not existing:
            return Response(
                {"status": False, "message": "Relation not found"},
                status=404
            )

        # -------- FETCH NAMES --------
        voter = VoterList.objects.filter(
            voter_list_id=voter_id
        ).only("voter_name_eng").first()

        related_voter = VoterList.objects.filter(
            voter_list_id=related_id
        ).only("voter_name_eng").first()

        voter_name = voter.voter_name_eng if voter else None
        related_voter_name = related_voter.voter_name_eng if related_voter else None

        # -------- LOG OLD DATA --------
        old_data = {
            "voter_name": voter_name,
            "related_voter_name": related_voter_name,
            "relation": relation,
            "reverse_relation": reverse,
        }

        # -------- DELETE BOTH SIDES --------
        VoterRelationshipDetails.objects.filter(
            voter_id=voter_id,
            related_voter_id=related_id,
            relation_with_voter=relation
        ).delete()

        if reverse:
            VoterRelationshipDetails.objects.filter(
                voter_id=related_id,
                related_voter_id=voter_id,
                relation_with_voter=reverse
            ).delete()

        # -------- LOG --------
        log_user_update(
            user=request.user,
            action="REMOVE_RELATION",
            voter_list_id=voter_id,
            description="Removed voter relationship",
            old_data=old_data,
            new_data=None,
        )
     
        return Response({
            "status": True,
            "message": "Deleted successfully"
        })

    except Exception as e:
        # print("REMOVE RELATION ERROR:", str(e))
        return Response(
            {"status": False, "message": "Server error"},
            status=500
        )
