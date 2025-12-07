from django.http import JsonResponse
from ..models import VoterList,VoterTag
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import IntegrityError

# update voter
@csrf_exempt
def update_voter(request, voter_list_id):

    if request.method != "PUT":
        return JsonResponse({"status": False, "message": "PUT method required"}, status=405)

    try:
        body = json.loads(request.body)

        # -------------------
        # GET EXISTING RECORD
        # -------------------
        try:
            voter = VoterList.objects.get(voter_list_id=voter_list_id)
        except VoterList.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Voter not found"
            }, status=404)

        # -------------------
        # INPUT VALUES
        # -------------------
        voter_id = body.get("voter_id")
        kramank = body.get("kramank")
        ward_no = body.get("ward_id")

        # -------------------
        # BASIC VALIDATION
        # -------------------
        if ward_no and ward_no not in [36, 37]:
            return JsonResponse({
                "status": False,
                "message": "ward_id must be 36 or 37"
            }, status=400)

        # -------------------
        # DUPLICATE CHECKS
        # exclude current row
        # -------------------
        if voter_id:
            if VoterList.objects.filter(voter_id=voter_id).exclude(voter_list_id=voter_list_id).exists():
                return JsonResponse({
                    "status": False,
                    "message": f"Duplicate voter_id: {voter_id}"
                }, status=409)

        if kramank:
            check_ward = ward_no if ward_no else voter.ward_no
        
            if VoterList.objects.filter(
                    kramank=kramank,
                    ward_no=check_ward
                ).exclude(voter_list_id=voter_list_id).exists():
        
                return JsonResponse({
                    "status": False,
                    "message": f"Duplicate kramank '{kramank}' in ward {check_ward}"
                }, status=409)


        # -------------------
        # TAG VALIDATION
        # -------------------
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

       # -------------------
        # UPDATE FIELDS
        # -------------------

        if voter_id:
            voter.voter_id = voter_id

        if kramank:
            voter.kramank = kramank

        if ward_no:
            voter.ward_no = ward_no

        # NAME FIELDS
        voter.first_name  = body.get("first_name", voter.first_name)
        voter.middle_name = body.get("middle_name", voter.middle_name)
        voter.last_name   = body.get("last_name", voter.last_name)

        # ADDRESS FIELDS
        voter.address_line1 = body.get("address", voter.address_line1)
        # voter.address_line2 = body.get("address_line2", voter.address_line2)
        # voter.address_line3 = body.get("address_line3", voter.address_line3)
        # voter.current_address = body.get("current_address",voter.current_address)

        # CONTACT FIELDS
        voter.mobile_no        = body.get("mobile_no", voter.mobile_no)
        voter.alternate_mobile1 = body.get("alternate_mobile_no1", voter.alternate_mobile1)
        voter.alternate_mobile2 = body.get("alternate_mobile_no2", voter.alternate_mobile2)
        voter.badge = body.get("badge",voter.badge)
        voter.location = body.get("location",voter.location)
        # OCCUPATION & OTHER INFO
        voter.occupation  = body.get("occupation", voter.occupation)
        voter.cast        = body.get("cast", voter.cast)
        voter.organisation = body.get("organisation", voter.organisation)

        # AGE & GENDER
        voter.age_eng    = body.get("age", voter.age_eng)
        voter.gender_eng = body.get("gender", voter.gender_eng)

        if tag_id:
            voter.tag_id = tag

        # -------------------
        # SAVE
        # -------------------
        voter.save()

        return JsonResponse({
            "status": True,
            "message": "Voter updated successfully",
            "voter_list_id": voter.voter_list_id,
            "sr_no": voter.sr_no
        })

    except IntegrityError:
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