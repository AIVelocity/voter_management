
from ..models import VoterList,VoterTag,VoterUserMaster,Occupation,Religion,Caste
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import IntegrityError
from .view_utils import log_user_update
from rest_framework_simplejwt.tokens import AccessToken

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_voter(request, voter_list_id):

    if request.method != "PUT":
        return Response({"status": False, "message": "PUT method required"}, status=405)

    try:
        auth_header = request.headers.get("Authorization")
        body = request.data
        
        user_id = None

        # Extract user_id from Bearer token
        # user = None
        if auth_header and auth_header.startswith("Bearer "):
            token_str = auth_header.split(" ")[1]
            try:
                token = AccessToken(token_str)
                user_id = token["user_id"]
                # user = VoterUserMaster.objects.get(user_id=user_id)
            except Exception:
                pass

        # user_id = body.get("user_id")  # coming from frontend after login
        ip = request.META.get("REMOTE_ADDR")

        # Get logged-in user
        user = None
        if user_id:
            try:
                user = VoterUserMaster.objects.get(user_id=user_id)
            except VoterUserMaster.DoesNotExist:
                user = None

        try:
            voter = VoterList.objects.get(voter_list_id=voter_list_id)
        except VoterList.DoesNotExist:
            return Response({"status": False, "message": "Voter not found"}, status=404)

        # Track changed fields
        changed_fields = {}

        def track(field, new_value):
            old_value = getattr(voter, field)
            if new_value != old_value:
                changed_fields[field] = {"old": old_value, "new": new_value}
                setattr(voter, field, new_value)

        # Now track only changed values
        track("address_line1", body.get("full_address", voter.address_line1))
        track("mobile_no", body.get("mobile_no", voter.mobile_no))
        track("alternate_mobile1", body.get("alternate_mobile_no1", voter.alternate_mobile1))
        track("alternate_mobile2", body.get("alternate_mobile_no2", voter.alternate_mobile2))
        track("badge", body.get("badge", voter.badge))
        track("location", body.get("location", voter.location))
        track("comments", body.get("comments", voter.comments))
        track("check_progress",body.get("check_progress",voter.check_progress))
        track("organisation", body.get("organisation",voter.organisation))
        # OCCUPATION update (ForeignKey)
        occupation = body.get("occupation")
        if occupation is not None:
            try:
                new_occupation = Occupation.objects.get(occupation_id=occupation)

                if voter.occupation != new_occupation:
                    changed_fields["occupation"] = {
                        "old": voter.occupation.occupation_id if voter.occupation else None,
                        "new": new_occupation.occupation_id
                    }
                    voter.occupation = new_occupation

            except Occupation.DoesNotExist:
                return Response({"status": False, "message": "Invalid occupation"}, status=400)

        # RELIGION update (ForeignKey)
        religion_id = body.get("religion_id")
        if religion_id is not None:
            try:
                new_religion = Religion.objects.get(religion_id=religion_id)

                if voter.religion != new_religion:
                    changed_fields["religion"] = {
                        "old": voter.religion.religion_id if voter.religion else None,
                        "new": new_religion.religion_id
                    }
                    voter.religion = new_religion

            except Religion.DoesNotExist:
                return Response({"status": False, "message": "Invalid religion_id"}, status=400)

        # CAST update (ForeignKey)
        caste_id = body.get("cast")
        if caste_id is not None:
            try:
                new_caste = Caste.objects.get(caste_id=caste_id)

                if voter.cast != new_caste:
                    changed_fields["cast"] = {
                        "old": voter.cast.caste_id if voter.cast else None,
                        "new": new_caste.caste_id
                    }
                    voter.cast = new_caste

            except Caste.DoesNotExist:
                return Response({"status": False, "message": "Invalid cast"}, status=400)

        # TAG update
        tag_id = body.get("tag_id")
        if tag_id:
            try:
                new_tag = VoterTag.objects.get(tag_id=tag_id)

                if voter.tag_id != new_tag:
                    changed_fields["tag_id"] = {
                        "old": voter.tag_id.tag_id if voter.tag_id else None,
                        "new": new_tag.tag_id
                    }
                    voter.tag_id = new_tag

            except VoterTag.DoesNotExist:
                return Response({"status": False, "message": "Invalid tag_id"}, status=400)

        # # If nothing changed, return message
        # if not changed_fields:
        #     return Response({"status": True, "message": "No changes detected"})

        voter.save()

        # Save to logs
        # Build dynamic action text
        if len(changed_fields) == 1:
            # Only 1 field changed → action describes that field
            field_name = list(changed_fields.keys())[0]
            action_text = f"UPDATED_{field_name.upper()}"
        else:
            # Multiple fields changed
            updated_list = ", ".join([f.upper() for f in changed_fields.keys()])
            action_text = f"UPDATED_MULTIPLE_FIELDS ({updated_list})"

        
        log_user_update(
            user=user,
            action=action_text,
            description=f"Updated voter {voter_list_id}",
            changed_fields=changed_fields,
            ip=ip,
            voter_list_id=voter_list_id
            
        )

        return Response({
            "status": True,
            "message": "Voter updated successfully",
            "updated_fields": changed_fields
        })

    except Exception as e:
        return Response({"status": False, "error": str(e)}, status=500)