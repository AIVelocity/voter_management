from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("",views.index,name="index"),
    path("voters/",views.voters_info,name="voters_info"),
    path("voters/<int:voter_list_id>/", views.single_voters_info,name="single_voters_info"),
    path("voter_add/",views.add_voter,name="add_voter"),
    path("voter_update/<int:voter_list_id>/", views.update_voter, name="update_voter"),
    path("tags/",views.tags,name="tags"),
    path("voters/search/", views.voters_search, name="voters_search"),
    path("voters/family_search/",views.family_dropdown_search, name = "family_dropdown_search"),
    path("roles/",views.roles,name="roles"),
    path("voters/relation_add/",views.add_relation,name="add_relation"),
    path("voters/relation_remove/",views.remove_relation,name="remove_relation")
]

# POST /api/voter/relation/add
# {
#   "voter_id": 100,
#   "related_voter_id": 200,
#   "relation": "child"
# }

