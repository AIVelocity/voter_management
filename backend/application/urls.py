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
    path("roles/",views.roles,name="roles")
]
