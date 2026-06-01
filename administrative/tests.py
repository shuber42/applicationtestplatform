"""Tests for the administrative app."""

from django.test import TestCase
from django.urls import reverse


class DashboardSmokeTests(TestCase):
    def test_dashboard_requires_login(self) -> None:
        response = self.client.get(reverse("administrative:dashboard"))
        # Unauthenticated users should be redirected to the login page.
        self.assertEqual(response.status_code, 302)
