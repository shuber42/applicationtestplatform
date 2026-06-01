"""URL configuration for the administrative app."""

from django.urls import path

from . import views

app_name = "administrative"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
