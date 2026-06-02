"""Django admin registrations for the applicants app."""

from __future__ import annotations

from django.contrib import admin

from .models import Applicant


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    search_fields = ("name", "email")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
