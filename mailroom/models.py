"""Models for the mailroom app.

Two concepts:

* :class:`MailTemplate` — a reusable subject/body pair authored by staff,
  rendered with the Django template engine. Variables like
  ``{{ applicant.name }}`` are substituted at send time from a context
  built from the addressed applicant plus any ad-hoc context passed by
  the caller.

* :class:`MailMessage` — the audit row for every individual message,
  inbound or outbound. Outbound rows record what was sent (and via which
  template, if any); inbound rows record the parsed envelope/body of
  messages pulled from IMAP. Linking back to an :class:`Applicant` lets
  the administrative UI render per-applicant threads.
"""

from __future__ import annotations

from django.db import models
from django.template import Context, Template
from django.utils import timezone

from applicants.models import Applicant


class MailTemplate(models.Model):
    """A reusable mail template authored by staff.

    The ``slug`` is the stable identifier used by services and
    management commands; the ``name`` is the human label rendered in
    the administrative UI.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    subject = models.CharField(max_length=998)
    body = models.TextField(
        help_text=(
            "Plain-text body. Django template syntax is supported; "
            "the rendering context contains 'applicant' plus any extra "
            "context passed by the caller."
        ),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def render(
        self,
        *,
        applicant: Applicant | None = None,
        context: dict | None = None,
    ) -> tuple[str, str]:
        """Render ``(subject, body)`` against the given context.

        ``applicant`` and any caller-supplied ``context`` keys are
        available to template variables. The caller-supplied context
        wins on key collisions so individual callers can override the
        default ``applicant`` binding if they need to.
        """

        render_context: dict = {"applicant": applicant}
        if context:
            render_context.update(context)
        django_context = Context(render_context)
        subject = Template(self.subject).render(django_context).strip()
        body = Template(self.body).render(django_context)
        return subject, body


class MailMessage(models.Model):
    """A single mail audit row (inbound or outbound)."""

    DIRECTION_OUTBOUND = "out"
    DIRECTION_INBOUND = "in"
    DIRECTION_CHOICES = (
        (DIRECTION_OUTBOUND, "Outbound"),
        (DIRECTION_INBOUND, "Inbound"),
    )

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_RECEIVED = "received"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
        (STATUS_RECEIVED, "Received"),
    )

    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    applicant = models.ForeignKey(
        Applicant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mail_messages",
    )
    template = models.ForeignKey(
        MailTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
    )
    from_address = models.EmailField()
    to_address = models.EmailField()
    subject = models.CharField(max_length=998)
    body = models.TextField()
    message_id = models.CharField(
        max_length=998,
        blank=True,
        db_index=True,
        help_text="RFC 5322 Message-ID of the message (without angle brackets).",
    )
    in_reply_to = models.CharField(
        max_length=998,
        blank=True,
        help_text="Message-ID of the message this is a reply to, if any.",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    raw = models.TextField(
        blank=True,
        help_text="Raw RFC 5322 source (inbound only, optional).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("direction", "status")),
            models.Index(fields=("applicant", "-created_at")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("direction", "message_id"),
                name="mailroom_mailmessage_unique_direction_msgid",
                condition=models.Q(message_id__gt=""),
            ),
        ]

    def __str__(self) -> str:
        arrow = "→" if self.direction == self.DIRECTION_OUTBOUND else "←"
        return f"{arrow} {self.to_address if self.direction == self.DIRECTION_OUTBOUND else self.from_address}: {self.subject}"

    def mark_sent(self, *, when: timezone.datetime | None = None) -> None:
        self.status = self.STATUS_SENT
        self.sent_at = when or timezone.now()
        self.error = ""
        self.save(update_fields=("status", "sent_at", "error", "updated_at"))

    def mark_failed(self, error: str) -> None:
        self.status = self.STATUS_FAILED
        self.error = error
        self.save(update_fields=("status", "error", "updated_at"))
