"""URL configuration for the applicants app."""

from django.urls import path

from . import views

app_name = "applicants"

urlpatterns = [
    path("", views.index, name="index"),
]
