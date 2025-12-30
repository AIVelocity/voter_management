from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from logger import logger
from ..models import (
    VoterList,
    VoterTag,
    VoterUserMaster,
    Occupation,
    Religion,
    Caste,
)
from .view_utils import rematch_contacts_for_voter, log_user_update


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_voter(request, voter_list_id):

    try:
        logger.info(f"update_api: Update voter request received for voter_list_id {voter_list_id}")
        body = request.data
        # auth_header = request.headers.get("Authorization")
        ip = request.META.get("REMOTE_ADDR")

        user = request.user
        
        try:
            voter = VoterList.objects.get(voter_list_id=voter_list_id)
        except VoterList.DoesNotExist:
            return Response(
                {"status": False, "message": "Voter not found"},
                status=404
            )

        # ---------- CHANGE TRACKING ----------
        changed_fields = {}

        def track(field, new_val):
            """
            Track and apply field changes safely.
            """
            if new_val is None:
                return

            old_val = getattr(voter, field)
            if new_val != old_val:
                changed_fields[field] = {
                    "old": old_val,
                    "new": new_val
                }
                setattr(voter, field, new_val)

        # ---------- PHONE SNAPSHOT (BEFORE) ----------
        old_numbers = {
            voter.mobile_no,
            voter.alternate_mobile1,
            voter.alternate_mobile2
        }

        # ---------- BASIC FIELD UPDATES ----------
        track("address_line1", body.get("full_address"))
        track("mobile_no", body.get("mobile_no"))
        track("alternate_mobile1", body.get("alternate_mobile_no1"))
        track("alternate_mobile2", body.get("alternate_mobile_no2"))
        track("badge", body.get("badge"))
        track("location", body.get("location"))
        track("comments", body.get("comments"))
        track("check_progress", body.get("check_progress"))
        track("organisation", body.get("organisation"))

        # ---------- FK UPDATES ----------
        occupation_id = body.get("occupation")
        if occupation_id is not None:
            try:
                new_occupation = Occupation.objects.get(
                    occupation_id=occupation_id
                )
                if voter.occupation != new_occupation:
                    changed_fields["occupation"] = {
                        "old": voter.occupation.occupation_name if voter.occupation else None,
                        "new": new_occupation.occupation_name
                    }
                    voter.occupation = new_occupation
            except Occupation.DoesNotExist:
                return Response(
                    {"status": False, "message": "Invalid occupation"},
                    status=400
                )

        religion_id = body.get("religion_id")
        if religion_id is not None:
            try:
                new_religion = Religion.objects.get(
                    religion_id=religion_id
                )
                if voter.religion != new_religion:
                    changed_fields["religion"] = {
                        "old": voter.religion.religion_name if voter.religion else None,
                        "new": new_religion.religion_name
                    }
                    voter.religion = new_religion
            except Religion.DoesNotExist:
                return Response(
                    {"status": False, "message": "Invalid religion_id"},
                    status=400
                )

        caste_id = body.get("cast")
        if caste_id is not None:
            try:
                new_caste = Caste.objects.get(caste_id=caste_id)
                if voter.cast != new_caste:
                    changed_fields["cast"] = {
                        "old": voter.cast.caste_name if voter.cast else None,
                        "new": new_caste.caste_name
                    }
                    voter.cast = new_caste
            except Caste.DoesNotExist:
                return Response(
                    {"status": False, "message": "Invalid cast"},
                    status=400
                )

        tag_id = body.get("tag_id")
        if tag_id is not None:
            try:
                new_tag = VoterTag.objects.get(tag_id=tag_id)
                if voter.tag_id != new_tag:
                    changed_fields["tag_id"] = {
                        "old": voter.tag_id.tag_name if voter.tag_id else None,
                        "new": new_tag.tag_name
                    }
                    voter.tag_id = new_tag
            except VoterTag.DoesNotExist:
                return Response(
                    {"status": False, "message": "Invalid tag_id"},
                    status=400
                )

        # ---------- SAVE ----------
        if changed_fields:
            voter.save()

        # ---------- PHONE SNAPSHOT (AFTER) ----------
        new_numbers = {
            voter.mobile_no,
            voter.alternate_mobile1,
            voter.alternate_mobile2
        }

        phone_changed = old_numbers != new_numbers

        if phone_changed:
            rematch_contacts_for_voter(voter,user)

        # ---------- LOGGING ----------
        if changed_fields:
            if len(changed_fields) == 1:
                field = list(changed_fields.keys())[0]
                action = f"UPDATED_{field.upper()}"
            else:
                fields = ", ".join(f.upper() for f in changed_fields.keys())
                action = f"UPDATED_MULTIPLE_FIELDS ({fields})"

            log_user_update(
                user=user,
                action=action,
                description=f"Updated voter {voter_list_id}",
                changed_fields=changed_fields,
                ip=ip,
                voter_list_id=voter_list_id
            )
        logger.info(f"update_api: Voter {voter_list_id} updated successfully with changes: {changed_fields}")
        return Response({
            "status": True,
            "message": "Voter updated successfully",
            "updated_fields": changed_fields
            # "phone_changed": phone_changed
        })

    except Exception as e:
        return Response(
            {"status": False, "error": str(e)},
            status=500
        )
