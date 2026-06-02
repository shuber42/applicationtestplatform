"""Tests for the administrative app."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core import mail as django_mail
from django.test import TestCase, override_settings
from django.urls import reverse

from applicants.models import Applicant
from mailroom.models import MailMessage, MailTemplate


class DashboardSmokeTests(TestCase):
    def test_dashboard_requires_login(self) -> None:
        response = self.client.get(reverse("administrative:dashboard"))
        # Unauthenticated users should be redirected to the login page.
        self.assertEqual(response.status_code, 302)


class _AuthenticatedAdministrativeTestCase(TestCase):
    """Shared fixtures for the staff-only administrative views."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="staff",
            password="testpass-123",
        )
        cls.template = MailTemplate.objects.create(
            name="Welcome",
            slug="welcome",
            subject="Hello {{ applicant.name }}",
            body="Hi {{ applicant.name }}, welcome.",
        )
        cls.applicant = Applicant.objects.create(
            name="Alice",
            email="alice@example.com",
        )

    def setUp(self) -> None:
        super().setUp()
        assert self.client.login(username="staff", password="testpass-123")


class AdministrativeViewsSmokeTests(_AuthenticatedAdministrativeTestCase):
    def test_dashboard_renders_stats(self) -> None:
        response = self.client.get(reverse("administrative:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administrative dashboard")
        self.assertContains(response, "1</strong> applicants")

    def test_applicant_list_renders(self) -> None:
        response = self.client.get(reverse("administrative:applicant_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.applicant.name)
        self.assertContains(response, self.applicant.email)

    def test_applicant_detail_includes_messages(self) -> None:
        MailMessage.objects.create(
            direction=MailMessage.DIRECTION_OUTBOUND,
            status=MailMessage.STATUS_SENT,
            applicant=self.applicant,
            template=self.template,
            from_address="noreply@local",
            to_address=self.applicant.email,
            subject="Hello Alice",
            body="Hi Alice.",
            message_id="abc@example.com",
        )
        response = self.client.get(
            reverse("administrative:applicant_detail", kwargs={"pk": self.applicant.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello Alice")
        self.assertContains(response, "Sent")

    def test_template_list_renders(self) -> None:
        response = self.client.get(reverse("administrative:template_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome")
        self.assertContains(response, "welcome")  # slug

    def test_template_create_persists_template(self) -> None:
        response = self.client.post(
            reverse("administrative:template_create"),
            data={
                "name": "Reminder",
                "slug": "reminder",
                "subject": "Reminder: {{ applicant.name }}",
                "body": "Please complete your test.",
                "is_active": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(MailTemplate.objects.filter(slug="reminder").exists())


class AdministrativeSendMailTests(_AuthenticatedAdministrativeTestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_form_sends_and_redirects_to_message_detail(self) -> None:
        django_mail.outbox = []

        response = self.client.post(
            reverse("administrative:mail_send"),
            data={
                "template": str(self.template.pk),
                "applicant": str(self.applicant.pk),
            },
        )
        self.assertEqual(response.status_code, 302)

        # One outbound MailMessage + one Django outbox entry.
        message = MailMessage.objects.get(
            direction=MailMessage.DIRECTION_OUTBOUND,
            applicant=self.applicant,
        )
        self.assertEqual(message.status, MailMessage.STATUS_SENT)
        self.assertEqual(len(django_mail.outbox), 1)
        self.assertIn("Hello Alice", django_mail.outbox[0].subject)
        self.assertTrue(response.url.endswith(
            reverse("administrative:message_detail", kwargs={"pk": message.pk})
        ))

    def test_message_list_filters_by_direction(self) -> None:
        MailMessage.objects.create(
            direction=MailMessage.DIRECTION_OUTBOUND,
            status=MailMessage.STATUS_SENT,
            applicant=self.applicant,
            from_address="noreply@local",
            to_address=self.applicant.email,
            subject="Outbound thing",
            body="hi",
        )
        MailMessage.objects.create(
            direction=MailMessage.DIRECTION_INBOUND,
            status=MailMessage.STATUS_RECEIVED,
            applicant=self.applicant,
            from_address=self.applicant.email,
            to_address="staff@local",
            subject="Inbound reply",
            body="bye",
        )

        response_out = self.client.get(
            reverse("administrative:message_list") + "?direction=out"
        )
        self.assertContains(response_out, "Outbound thing")
        self.assertNotContains(response_out, "Inbound reply")

        response_in = self.client.get(
            reverse("administrative:message_list") + "?direction=in"
        )
        self.assertContains(response_in, "Inbound reply")
        self.assertNotContains(response_in, "Outbound thing")
