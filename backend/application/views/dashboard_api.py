from ..models import VoterList
from django.db.models import Count
from django.http import JsonResponse

# from django.views.decorators.csrf import csrf_exempt

# @csrf_exempt
def dashboard(request):
    
    total_voters = VoterList.objects.count()
    # voter_list_count = VoterList.objects.filter(vo)
    return JsonResponse({
        "total_voters" : total_voters
    })