"""Views for the applicants app.

Currently exposes a lightweight landing page so the route surface is
verifiable. Concrete views for taking and submitting a test are
introduced in follow-up issues.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def index(request: HttpRequest) -> HttpResponse:
    """Render the applicant-facing landing page."""
    return render(request, "applicants/index.html")
