"""Tests for the applicants app."""

from __future__ import annotations

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import Applicant


class IndexSmokeTests(TestCase):
    def test_index_renders(self) -> None:
        response = self.client.get(reverse("applicants:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Test Platform")


class ApplicantModelTests(TestCase):
    def test_str_includes_name_and_email(self) -> None:
        applicant = Applicant.objects.create(name="Alice", email="alice@example.com")
        self.assertEqual(str(applicant), "Alice <alice@example.com>")

    def test_email_is_unique(self) -> None:
        Applicant.objects.create(name="Alice", email="alice@example.com")
        with self.assertRaises(IntegrityError):
            Applicant.objects.create(name="Alice 2", email="alice@example.com")

    def test_default_ordering_is_by_name_then_email(self) -> None:
        Applicant.objects.create(name="Charlie", email="c@example.com")
        Applicant.objects.create(name="Alice", email="a@example.com")
        Applicant.objects.create(name="Bob", email="b@example.com")
        names = list(Applicant.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Alice", "Bob", "Charlie"])
