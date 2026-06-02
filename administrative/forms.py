"""Forms for the administrative app."""

from __future__ import annotations

from django import forms

from applicants.models import Applicant
from mailroom.models import MailTemplate


class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ("name", "email", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class MailTemplateForm(forms.ModelForm):
    class Meta:
        model = MailTemplate
        fields = ("name", "slug", "subject", "body", "is_active")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 14}),
        }
        help_texts = {
            "slug": "Stable identifier used by services and management commands.",
            "body": (
                "Plain text. Use Django template syntax for variables, "
                "for example: Hello {{ applicant.name }}."
            ),
        }


class SendMailForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=MailTemplate.objects.filter(is_active=True),
        label="Mail template",
    )
    applicant = forms.ModelChoiceField(
        queryset=Applicant.objects.all(),
        label="Applicant",
    )
