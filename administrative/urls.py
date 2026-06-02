"""URL configuration for the administrative app."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "administrative"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Applicants
    path("applicants/", views.applicant_list, name="applicant_list"),
    path("applicants/new/", views.applicant_create, name="applicant_create"),
    path("applicants/<int:pk>/", views.applicant_detail, name="applicant_detail"),
    path("applicants/<int:pk>/edit/", views.applicant_update, name="applicant_update"),
    # Mail templates
    path("mail/templates/", views.template_list, name="template_list"),
    path("mail/templates/new/", views.template_create, name="template_create"),
    path(
        "mail/templates/<int:pk>/edit/",
        views.template_update,
        name="template_update",
    ),
    # Send + history
    path("mail/send/", views.mail_send, name="mail_send"),
    path("mail/messages/", views.message_list, name="message_list"),
    path("mail/messages/<int:pk>/", views.message_detail, name="message_detail"),
]
