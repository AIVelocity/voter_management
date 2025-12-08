from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("",views.index,name="index"),
    # voter list
    path("voters/",views.voters_info,name="voters_info"),
    # single voter info
    path("voters/<int:voter_list_id>/", views.single_voters_info,name="single_voters_info"),
    # voter addition
    path("voter_add/",views.add_voter,name="add_voter"),
    # voter update
    path("voter_update/<int:voter_list_id>/", views.update_voter, name="update_voter"),
    # tags
    path("tags/",views.tags,name="tags"),
    # voter search api
    path("voters/search/", views.voters_search, name="voters_search"),
    # voter family search
    path("voters/family_search/",views.family_dropdown_search, name = "family_dropdown_search"),
    # roles
    path("roles/",views.roles,name="roles"),
    # voter relation add
    path("voters/relation_add/",views.add_relation,name="add_relation"),
    # voter relation remove
    path("voters/relation_remove/",views.remove_relation,name="remove_relation"),
    # dashboard 
    path("admin/dashboard/",views.dashboard,name="dashboard"),
    # filter 
    path("voters/filter/",views.filter,name="filter")
]

# POST /api/voter/relation/add
# {
#   "voter_id": 100,
#   "related_voter_id": 200,
#   "relation": "child"
# }

