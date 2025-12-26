from ..models import VoterList,VoterUserMaster
from django.core.cache import cache
from django.core.paginator import Paginator
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import os
import base64
from django.http import FileResponse


BASE_DIR = settings.BASE_DIR
print(BASE_DIR)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def voters_info_photo(request): 
    # data = request.body
    try:
        auth_header = request.headers.get("Authorization")
        data = request.GET
        
        # user_id = None
        voter_list_id =data.get("voter_list_id")

        # # Extract user_id from Bearer token
        # # user = None
        # if auth_header and auth_header.startswith("Bearer "):
        #     token_str = auth_header.split(" ")[1]
        #     try:
        #         token = AccessToken(token_str)
        #         user_id = token["user_id"]
        #         # user = VoterUserMaster.objects.get(user_id=user_id)
        #     except Exception:
        #         pass


        # # Get logged-in user
        # user = None
        # if user_id:
        #     try:
        #         user = VoterUserMaster.objects.get(user_id=user_id)
        #     except VoterUserMaster.DoesNotExist:
        #         user = None

        try:
            voter = VoterList.objects.get(voter_list_id=voter_list_id)
        except VoterList.DoesNotExist:
            return Response({"status": False, "message": "Voter not found"}, status=404)

        image_name = voter.image_name
        
        image_full_path = os.path.join(BASE_DIR,'images','Cropped_detected_boxes',image_name)
        print(image_full_path)
        
<<<<<<< HEAD
        if not os.path.exists(image_full_path):
            raise Exception("Image not found")
        
        return FileResponse(open(image_full_path, "rb"), content_type="image/png")
    
=======
        with open(image_full_path, "rb") as img_file:
            encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
        
        # ---------- RESPONSE ----------
        return Response({
            "status": True,
            "voter_id": voter.voter_list_id,
            "image_base64": f"data:image/png;base64,{encoded_image}"
        })
>>>>>>> eb81c87bb04a8e95db1e5fb2d87e801e16dce5f2
    except Exception as e:
        return Response({"status": False, "message": str(e)}, status=500)
    
    