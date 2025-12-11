from ..models import VoterList
from django.db.models import Count
from django.http import JsonResponse

# from django.views.decorators.csrf import csrf_exempt

# @csrf_exempt
def dashboard(request):
    
    total_voters = VoterList.objects.count()
    # voter_list_count = VoterList.objects.filter(vo)
    golden_color_tags = VoterList.objects.filter(tag_id = 4)
    red_color_tags = VoterList.objects.filter(tag_id = 3)
    orange_color_tags = VoterList.objects.filter(tag_id = 2)
    green_color_tags = VoterList.objects.filter(tag_id = 1)
    
    
    
    return JsonResponse({
        "total_voters" : total_voters
    })