from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("",views.index,name="index"),
    path("voters/",views.voters_info,name="voters_info"),
]
