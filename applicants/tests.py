"""Tests for the applicants app."""

from django.test import TestCase
from django.urls import reverse


class IndexSmokeTests(TestCase):
    def test_index_renders(self) -> None:
        response = self.client.get(reverse("applicants:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Test Platform")
