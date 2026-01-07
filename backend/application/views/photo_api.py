from ..models import VoterList
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import os
import base64
from logger import logger


BASE_DIR = settings.BASE_DIR
# print(BASE_DIR)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def voters_info_photo(request): 
    # data = request.body
    try:
        logger.info("photo_api: Voter photo request received")
        data = request.GET
        # user_id = None
        voter_list_id =data.get("voter_list_id")

        try:
            voter = VoterList.objects.get(voter_list_id=voter_list_id)
        except VoterList.DoesNotExist:
            return Response({"status": False, "message": "Voter not found"}, status=404)

        image_name = voter.image_name
        
        image_full_path = os.path.join(BASE_DIR,'images','Cropped_detected_boxes',image_name)
        # print(image_full_path)
        
        with open(image_full_path, "rb") as img_file:
            encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
            
        logger.info(f"photo_api: Photo for voter {voter.voter_list_id} retrieved successfully")
        # ---------- RESPONSE ----------
        return Response({
            "status": True,
            "voter_id": voter.voter_list_id,
            "image_base64": f"data:image/png;base64,{encoded_image}"
        })
    except Exception as e:
        return Response({"status": False, "message": str(e)}, status=500)
    
    