from django.http import JsonResponse
from ..models import VoterList,VoterTag
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from logger import logger

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_voter(request):

    if request.method != "POST":
        return JsonResponse({"status": False, "message": "POST method required"}, status=405)

    try:
        body = json.loads(request.body)

        # Required fields
        voter_id = body.get("voter_id")
        kramank = body.get("kramank")
        ward_no = body.get("ward_id")

        if not voter_id:
            return JsonResponse({"status": False, "message": "voter_id is required"}, status=400)

        if not kramank:
            return JsonResponse({"status": False, "message": "kramank is required"}, status=400)

        if not ward_no:
            return JsonResponse({"status": False, "message": "ward_id is required"}, status=400)

        if ward_no not in [37,36]:
            return JsonResponse({"status":False,"message":"ward id must be 36 or 37"})
        #  DUPLICATE CHECKS 

        if VoterList.objects.filter(voter_id=voter_id).exists():
            return JsonResponse({
                "status": False,
                "message": f"Duplicate voter_id found: {voter_id}"
            }, status=409)

        if VoterList.objects.filter(kramank=kramank, ward_no=ward_no).exists():
            return JsonResponse({
                "status": False,
                "message": f"Duplicate kramank found in ward {ward_no}: {kramank}"
            }, status=409)


        # TAG VALIDATION
        tag = None
        tag_id = body.get("tag_id")

        if tag_id:
            try:
                tag = VoterTag.objects.get(tag_id=tag_id)
            except VoterTag.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Invalid tag_id"
                }, status=400)


        # CREATE VOTER
        # (sr_no is NOT provided — trigger inserts it!)
        voter = VoterList.objects.create(
            voter_id=voter_id,
            # voter_name_marathi=body.get("voter_name_marathi"),
            # voter_name_eng=body.get("voter_name_eng"),
            first_name=body.get("first_name"),
            middle_name=body.get("middle_name"),
            last_name=body.get("last_name"),

            kramank=kramank,
            # tag_id = tag_id,
            
            # permanent_address=body.get("address"),
            # current_address=body.get("address"),
            address_line1 = body.get("address_line1"),
            address_line2 = body.get("address_line2"),
            address_line3 = body.get("address_line3"),

            mobile_no=body.get("mobile_no"),
            alternate_mobile1=body.get("alternate_mobile_no1"),
            alternate_mobile2=body.get("alternate_mobile_no2"),
            occupation = body.get("occupation"),
            cast = body.get("cast"),
            organisation = body.get("organisation"),

            age_eng=body.get("age"),
            gender_eng=body.get("gender"),

            ward_no=ward_no,
            tag_id=tag
        )

        voter.refresh_from_db()
        return JsonResponse({
            "status": True,
            "message": "Voter added successfully",
            "voter_list_id": voter.voter_list_id,
            "sr_no": voter.sr_no      # send back generated sr_no
        })
    
    except IntegrityError:
        # Safety net if DB unique constraint fails
        return JsonResponse({
            "status": False,
            "message": "Duplicate entry detected"
        }, status=409)

    except json.JSONDecodeError:
        return JsonResponse({
            "status": False,
            "message": "Invalid JSON body"
        }, status=400)

    except Exception as e:
        return JsonResponse({
            "status": False,
            "error": str(e)
        }, status=500)