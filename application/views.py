from django.http import JsonResponse
from .models import VoterList,VoterTag
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import IntegrityError

from django.db.models import Q

def index(request):
    return JsonResponse ({
        "status": True,
        "message":"Application running"
    })
    
# tags api
def tags(request):
    tags = VoterTag.objects.all().order_by("tag_id")
    data = []
    for tag in tags:
        data.append({
            "tag_id":tag.tag_id,
            "tag_name":tag.tag_name,
        })
    return JsonResponse({
        "status":True,
        "data":data
    })
   
# all voters list 
def voters_info(request):

    voters = VoterList.objects.select_related("tag_id").all().order_by("ward_no", "voter_list_id")[:100]   # limit for safety

    data = []

    for v in voters:
        data.append({
            "voter_list_id": v.voter_list_id,
            # "sr_no": v.sr_no,
            "voter_id": v.voter_id,
            "voter_name_marathi": v.voter_name_marathi,
            "voter_name_eng": v.voter_name_eng,
            "kramank": v.kramank,
            # "permanent_address": v.permanent_address,
            # "current_address":v.current_address,
            # "age": v.age,
            # "gender": v.gender,
            "age":v.age_eng,
            "gender":v.gender_eng,
            # "image_name": v.image_name,
            "ward_id": v.ward_no,
            "tag": v.tag_id.tag_name if v.tag_id else None,
            "badge":v.badge,
            "location":v.location
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })




# single voter info
def single_voters_info(request, voter_list_id):

    try:
        voter = VoterList.objects.select_related("tag_id").get(
            voter_list_id=voter_list_id
        )
    except VoterList.DoesNotExist:
        return JsonResponse({
            "status": False,
            "message": "Voter not found"
        }, status=404)


    # ---------------- HELPERS ----------------

    def safe_age(v):
        val = str(v or "").lower().strip()
        try:
            return int(val, 16) if val.startswith("0x") else int(val)
        except:
            return None

    def parse_kramank(value):
        try:
            return int(str(value).split("/")[-1])
        except:
            return 0


    # ---------------- COMPUTE ----------------

    age = safe_age(voter.age_eng)
    kramank = parse_kramank(voter.kramank)

    address = (voter.address_line1 or "") + \
              (voter.address_line2 or "") + \
              (voter.address_line3 or "")

    fname = voter.first_name
    parent_name = voter.middle_name
    surname = voter.last_name


    # ---------------- RELATIVES (IN PYTHON) ----------------

    relatives = [
        r for r in VoterList.objects.filter(last_name=surname)
        if abs(parse_kramank(r.kramank) - kramank) <= 10
    ]


    # ---------------- FATHER ----------------
    father_name = " ".join(filter(None, [
    voter.middle_name,
    voter.last_name
    ]))


    data = {
        "voter_list_id": voter.voter_list_id,
        "sr_no": voter.sr_no,
        "voter_id": voter.voter_id,
        "first_name": voter.first_name,
        "middle_name": voter.middle_name,
        "last_name": voter.last_name,

        "kramank": voter.kramank,
        "address": address,

        "mobile_no": voter.mobile_no,
        "alternate_mobile_no1": voter.alternate_mobile1,
        "alternate_mobile_no2": voter.alternate_mobile2,

        "age": age,
        "gender": voter.gender_eng,
        "ward_id": voter.ward_no,
        "tag": voter.tag_id.tag_name if voter.tag_id else None,

        # "mother_name": mother_name,
        "father_name": father_name,
        # "children": children,
        # "siblings": [brothers + ["sisters"]],
        "other_family_members":""
    }

    return JsonResponse({"status": True, "data": data})

# single voter info page
# def single_voters_info(request, voter_list_id):

#     try:
#         voter = VoterList.objects.select_related("tag_id").get(
#             voter_list_id=voter_list_id
#         )

#     except VoterList.DoesNotExist:
#         return JsonResponse({
#             "status": False,
#             "message": "Voter not found"
#         }, status=404)
        
#     address = (
#     (voter.address_line1 or "") +
#     (voter.address_line2 or "") +
#     (voter.address_line3 or "")
# )

#     data = {
#     "voter_list_id": voter.voter_list_id,
#     "sr_no": voter.sr_no,
#     "voter_id": voter.voter_id,

#     "first_name": voter.first_name,
#     "middle_name": voter.middle_name,
#     "last_name": voter.last_name,

#     "kramank": voter.kramank,

#     # "permanent_address": voter.permanent_address,
#     # "current_address": voter.current_address,
#     "address":address,

#     "mobile_no": voter.mobile_no,
#     "alternate_mobile_no1": voter.alternate_mobile1,
#     "alternate_mobile_no2": voter.alternate_mobile2,

#     # safely handle hex or empty age_eng
#     "age": (
#         int(voter.age_eng, 16)
#         if voter.age_eng and str(voter.age_eng).lower().startswith("0x")
#         else int(voter.age_eng)
#         if voter.age_eng and str(voter.age_eng).isdigit()
#         else None
#     ),

#     "gender": voter.gender_eng,

#     "ward_id": voter.ward_no,

#     # safe FK access
#     "tag": voter.tag_id.tag_name if voter.tag_id else None,

#     # extra optional fields
#     "mother_name": "",
#     "father_name": "",
#     "children": [],
#     "brothers": [],
# }

#     return JsonResponse({
#         "status": True,
#         "data": data
#     })

# add a new voter
@csrf_exempt
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

            # permanent_address=body.get("address"),
            # current_address=body.get("address"),
            address_line1 = body.get("address_line1"),
            address_line2 = body.get("address_line2"),
            address_line3 = body.get("address_line3"),

            mobile_no=body.get("mobile_no"),
            alternate_mobile1=body.get("alternate_mobile_no1"),
            alternate_mobile2=body.get("alternate_mobile_no2"),

            age_eng=body.get("age"),
            gender_eng=body.get("gender"),

            ward_no=ward_no,
            tag_id=tag
        )
# image_name=body.get("image_name")
        

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
        # Only update fields provided in body

        if voter_id:
            voter.voter_id = voter_id

        if kramank:
            voter.kramank = kramank

        if ward_no:
            voter.ward_no = ward_no

        # voter.voter_name_marathi = body.get("voter_name_marathi", voter.voter_name_marathi)
        # voter.voter_name_eng = body.get("voter_name_eng", voter.voter_name_eng)
        voter.last_name=body.get("last_name",voter.last_name)
        voter.middle_name=body.get("middle_name",voter.middle_name)
        voter.first_name=body.get("first_name",voter.first_name)
        voter.current_address = body.get("current_address", voter.current_address)
        voter.permanent_address =  body.get("permanent_address",voter.permanent_address)
        voter.age_eng = body.get("age", voter.age)
        voter.gender_eng = body.get("gender", voter.gender)

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
