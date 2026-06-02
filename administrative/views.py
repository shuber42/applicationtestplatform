"""Views for the administrative app.

Exposes a lightweight staff-only UI for:

* Managing applicants (create/edit + per-applicant message thread).
* Authoring mail templates.
* Sending a template to an applicant.
* Reviewing inbound/outbound mail history.
"""

from __future__ import annotations

from django.contrib import messages as flash
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from applicants.models import Applicant
from mailroom.models import MailMessage, MailTemplate
from mailroom.services.sender import MailSendError, send_template_to_applicant

from .forms import ApplicantForm, MailTemplateForm, SendMailForm


@login_required
@require_http_methods(["GET"])
def dashboard(request: HttpRequest) -> HttpResponse:
    """Render the administrative dashboard landing page."""

    context = {
        "applicant_count": Applicant.objects.count(),
        "template_count": MailTemplate.objects.count(),
        "outbound_count": MailMessage.objects.filter(
            direction=MailMessage.DIRECTION_OUTBOUND
        ).count(),
        "inbound_count": MailMessage.objects.filter(
            direction=MailMessage.DIRECTION_INBOUND
        ).count(),
    }
    return render(request, "administrative/dashboard.html", context)


# ---------------------------------------------------------------------------
# Applicants
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET"])
def applicant_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "administrative/applicant_list.html",
        {"applicants": Applicant.objects.all()},
    )


@login_required
@require_http_methods(["GET", "POST"])
def applicant_create(request: HttpRequest) -> HttpResponse:
    form = ApplicantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        applicant = form.save()
        flash.success(request, f"Created applicant {applicant}.")
        return redirect("administrative:applicant_detail", pk=applicant.pk)
    return render(
        request,
        "administrative/applicant_form.html",
        {"form": form, "mode": "create"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def applicant_update(request: HttpRequest, pk: int) -> HttpResponse:
    applicant = get_object_or_404(Applicant, pk=pk)
    form = ApplicantForm(request.POST or None, instance=applicant)
    if request.method == "POST" and form.is_valid():
        form.save()
        flash.success(request, "Applicant updated.")
        return redirect("administrative:applicant_detail", pk=applicant.pk)
    return render(
        request,
        "administrative/applicant_form.html",
        {"form": form, "mode": "edit", "applicant": applicant},
    )


@login_required
@require_http_methods(["GET"])
def applicant_detail(request: HttpRequest, pk: int) -> HttpResponse:
    applicant = get_object_or_404(Applicant, pk=pk)
    return render(
        request,
        "administrative/applicant_detail.html",
        {
            "applicant": applicant,
            "messages_": applicant.mail_messages.all().select_related("template"),
        },
    )


# ---------------------------------------------------------------------------
# Mail templates
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET"])
def template_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "administrative/template_list.html",
        {"templates": MailTemplate.objects.all()},
    )


@login_required
@require_http_methods(["GET", "POST"])
def template_create(request: HttpRequest) -> HttpResponse:
    form = MailTemplateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        template = form.save()
        flash.success(request, f"Created template '{template.name}'.")
        return redirect("administrative:template_list")
    return render(
        request,
        "administrative/template_form.html",
        {"form": form, "mode": "create"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def template_update(request: HttpRequest, pk: int) -> HttpResponse:
    template = get_object_or_404(MailTemplate, pk=pk)
    form = MailTemplateForm(request.POST or None, instance=template)
    if request.method == "POST" and form.is_valid():
        form.save()
        flash.success(request, "Template updated.")
        return redirect("administrative:template_list")
    return render(
        request,
        "administrative/template_form.html",
        {"form": form, "mode": "edit", "template": template},
    )


# ---------------------------------------------------------------------------
# Send mail
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def mail_send(request: HttpRequest) -> HttpResponse:
    initial = {}
    template_pk = request.GET.get("template")
    applicant_pk = request.GET.get("applicant")
    if template_pk:
        initial["template"] = template_pk
    if applicant_pk:
        initial["applicant"] = applicant_pk

    form = SendMailForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        template = form.cleaned_data["template"]
        applicant = form.cleaned_data["applicant"]
        try:
            message = send_template_to_applicant(
                template=template,
                applicant=applicant,
            )
        except MailSendError as exc:
            flash.error(request, f"Send failed: {exc}")
            return redirect(reverse("administrative:mail_send"))
        flash.success(
            request,
            f"Sent '{template.name}' to {applicant.email} (message id {message.pk}).",
        )
        return redirect("administrative:message_detail", pk=message.pk)

    return render(request, "administrative/mail_send.html", {"form": form})


# ---------------------------------------------------------------------------
# Mail history
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET"])
def message_list(request: HttpRequest) -> HttpResponse:
    direction = request.GET.get("direction")
    qs = MailMessage.objects.select_related("applicant", "template")
    if direction in {MailMessage.DIRECTION_INBOUND, MailMessage.DIRECTION_OUTBOUND}:
        qs = qs.filter(direction=direction)
    return render(
        request,
        "administrative/message_list.html",
        {"mail_messages": qs[:200], "filter_direction": direction or ""},
    )


@login_required
@require_http_methods(["GET"])
def message_detail(request: HttpRequest, pk: int) -> HttpResponse:
    message = get_object_or_404(MailMessage, pk=pk)
    return render(
        request,
        "administrative/message_detail.html",
        {"mail_message": message},
    )
