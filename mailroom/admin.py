"""Django admin registrations for the mailroom app."""

from __future__ import annotations

from django.contrib import admin

from .models import MailMessage, MailTemplate


@admin.register(MailTemplate)
class MailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "subject", "body")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(MailMessage)
class MailMessageAdmin(admin.ModelAdmin):
    list_display = (
        "direction",
        "status",
        "subject",
        "from_address",
        "to_address",
        "applicant",
        "created_at",
    )
    list_filter = ("direction", "status", "template")
    search_fields = (
        "subject",
        "from_address",
        "to_address",
        "message_id",
        "body",
    )
    autocomplete_fields = ("applicant", "template")
    readonly_fields = (
        "direction",
        "from_address",
        "to_address",
        "subject",
        "body",
        "message_id",
        "in_reply_to",
        "sent_at",
        "received_at",
        "error",
        "raw",
        "created_at",
        "updated_at",
    )
