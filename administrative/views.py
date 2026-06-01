"""Views for the administrative app.

Currently exposes a lightweight dashboard so the route surface is
verifiable. Concrete CRUD views for question and test management are
introduced in follow-up issues.
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def dashboard(request: HttpRequest) -> HttpResponse:
    """Render the administrative dashboard landing page."""
    return render(request, "administrative/dashboard.html")
