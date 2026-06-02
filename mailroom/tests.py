"""Tests for the mailroom app: templates, sender, and inbound fetcher."""

from __future__ import annotations

from datetime import UTC, datetime
from email.message import EmailMessage as StdlibEmailMessage
from email.utils import format_datetime
from io import StringIO

import pytest
from django.core import mail as django_mail
from django.core.management import call_command
from django.core.management.base import CommandError

from applicants.models import Applicant
from mailroom.models import MailMessage, MailTemplate
from mailroom.services.fetcher import (
    ParsedInboundMessage,
    ingest_inbound_message,
    ingest_many,
    parse_inbound,
)
from mailroom.services.sender import MailSendError, send_template_to_applicant

# ---------------------------------------------------------------------------
# MailTemplate.render
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_template_render_substitutes_applicant_fields() -> None:
    template = MailTemplate.objects.create(
        name="Welcome",
        slug="welcome",
        subject="Hello {{ applicant.name }}",
        body="Hi {{ applicant.name }}, your email is {{ applicant.email }}.",
    )
    applicant = Applicant.objects.create(name="Alice", email="alice@example.com")

    subject, body = template.render(applicant=applicant)

    assert subject == "Hello Alice"
    assert "Hi Alice" in body
    assert "alice@example.com" in body


@pytest.mark.django_db
def test_template_render_merges_extra_context() -> None:
    template = MailTemplate.objects.create(
        name="Test invite",
        slug="invite",
        subject="Your {{ role }} test",
        body="Hi {{ applicant.name }}, take your {{ role }} test now.",
    )
    applicant = Applicant.objects.create(name="Bob", email="bob@example.com")

    subject, body = template.render(applicant=applicant, context={"role": "Engineer"})

    assert subject == "Your Engineer test"
    assert "Bob" in body
    assert "Engineer" in body


# ---------------------------------------------------------------------------
# send_template_to_applicant
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_send_template_creates_outbox_entry_and_audit_row(settings) -> None:
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    django_mail.outbox = []

    template = MailTemplate.objects.create(
        name="Welcome",
        slug="welcome",
        subject="Hello {{ applicant.name }}",
        body="Hi {{ applicant.name }}.",
    )
    applicant = Applicant.objects.create(name="Alice", email="alice@example.com")

    message = send_template_to_applicant(template=template, applicant=applicant)

    assert len(django_mail.outbox) == 1
    sent = django_mail.outbox[0]
    assert sent.subject == "Hello Alice"
    assert "Hi Alice" in sent.body
    assert sent.to == ["Alice <alice@example.com>"]
    assert sent.extra_headers.get("Message-ID", "").startswith("<")

    assert message.direction == MailMessage.DIRECTION_OUTBOUND
    assert message.status == MailMessage.STATUS_SENT
    assert message.applicant_id == applicant.pk
    assert message.template_id == template.pk
    assert message.to_address == "alice@example.com"
    assert message.subject == "Hello Alice"
    assert message.sent_at is not None
    assert message.message_id  # populated, no angle brackets


@pytest.mark.django_db
def test_send_template_refuses_inactive_template() -> None:
    template = MailTemplate.objects.create(
        name="Old",
        slug="old",
        subject="x",
        body="y",
        is_active=False,
    )
    applicant = Applicant.objects.create(name="Carla", email="c@example.com")

    with pytest.raises(MailSendError):
        send_template_to_applicant(template=template, applicant=applicant)

    assert MailMessage.objects.count() == 0


# ---------------------------------------------------------------------------
# parse_inbound + ingest
# ---------------------------------------------------------------------------


def _build_raw_message(
    *,
    from_address: str,
    to_address: str,
    subject: str,
    body: str,
    message_id: str | None = "msg-1@example.com",
    in_reply_to: str | None = None,
    date: datetime | None = None,
) -> bytes:
    msg = StdlibEmailMessage()
    msg["From"] = from_address
    msg["To"] = to_address
    msg["Subject"] = subject
    if message_id:
        msg["Message-ID"] = f"<{message_id}>"
    if in_reply_to:
        msg["In-Reply-To"] = f"<{in_reply_to}>"
    if date is None:
        date = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    msg["Date"] = format_datetime(date)
    msg.set_content(body)
    return bytes(msg)


def test_parse_inbound_extracts_envelope_and_body() -> None:
    raw = _build_raw_message(
        from_address="Alice <alice@example.com>",
        to_address="staff@datajob.local",
        subject="Re: Welcome",
        body="Thanks for the invite!\n",
        message_id="reply-1@example.com",
        in_reply_to="welcome-1@example.com",
    )

    parsed = parse_inbound(raw)

    assert isinstance(parsed, ParsedInboundMessage)
    assert parsed.from_address == "alice@example.com"
    assert parsed.to_address == "staff@datajob.local"
    assert parsed.subject == "Re: Welcome"
    assert "Thanks for the invite" in parsed.body
    assert parsed.message_id == "reply-1@example.com"
    assert parsed.in_reply_to == "welcome-1@example.com"
    assert parsed.received_at is not None


@pytest.mark.django_db
def test_ingest_inbound_links_to_known_applicant() -> None:
    applicant = Applicant.objects.create(name="Alice", email="alice@example.com")
    raw = _build_raw_message(
        from_address="Alice <alice@example.com>",
        to_address="staff@datajob.local",
        subject="Hello back",
        body="Hi there.",
        message_id="hi-1@example.com",
    )

    message = ingest_inbound_message(raw)

    assert message is not None
    assert message.direction == MailMessage.DIRECTION_INBOUND
    assert message.status == MailMessage.STATUS_RECEIVED
    assert message.applicant_id == applicant.pk
    assert message.from_address == "alice@example.com"
    assert message.subject == "Hello back"
    assert "Hi there" in message.body
    assert message.message_id == "hi-1@example.com"
    assert message.raw  # raw stored


@pytest.mark.django_db
def test_ingest_inbound_unknown_sender_creates_row_without_applicant() -> None:
    raw = _build_raw_message(
        from_address="stranger@elsewhere.test",
        to_address="staff@datajob.local",
        subject="Random",
        body="who knows",
        message_id="stranger-1@example.com",
    )

    message = ingest_inbound_message(raw)

    assert message is not None
    assert message.applicant is None
    assert message.from_address == "stranger@elsewhere.test"


@pytest.mark.django_db
def test_ingest_inbound_is_idempotent_on_message_id() -> None:
    raw = _build_raw_message(
        from_address="alice@example.com",
        to_address="staff@datajob.local",
        subject="Dup",
        body="dup body",
        message_id="dup-1@example.com",
    )

    first = ingest_inbound_message(raw)
    second = ingest_inbound_message(raw)

    assert first is not None
    assert second is None
    assert MailMessage.objects.filter(message_id="dup-1@example.com").count() == 1


@pytest.mark.django_db
def test_ingest_many_returns_only_new_rows() -> None:
    Applicant.objects.create(name="Alice", email="alice@example.com")
    raws = [
        _build_raw_message(
            from_address="alice@example.com",
            to_address="staff@datajob.local",
            subject=f"Msg {i}",
            body=f"body {i}",
            message_id=f"id-{i}@example.com",
        )
        for i in range(3)
    ]
    # Re-feeding the first one in should not double-create
    raws.append(raws[0])

    rows = ingest_many(raws)

    assert len(rows) == 3
    assert MailMessage.objects.filter(direction=MailMessage.DIRECTION_INBOUND).count() == 3


# ---------------------------------------------------------------------------
# Management commands
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_send_mail_template_command_invokes_sender(settings) -> None:
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    django_mail.outbox = []
    MailTemplate.objects.create(
        name="Welcome",
        slug="welcome",
        subject="Hi {{ applicant.name }}",
        body="Welcome {{ applicant.name }}.",
    )
    Applicant.objects.create(name="Alice", email="alice@example.com")

    out = StringIO()
    call_command(
        "send_mail_template", "welcome", "alice@example.com", stdout=out
    )

    assert "Sent template 'welcome'" in out.getvalue()
    assert len(django_mail.outbox) == 1
    assert MailMessage.objects.filter(
        direction=MailMessage.DIRECTION_OUTBOUND
    ).count() == 1


@pytest.mark.django_db
def test_send_mail_template_command_unknown_template() -> None:
    Applicant.objects.create(name="Alice", email="alice@example.com")
    with pytest.raises(CommandError, match="No MailTemplate"):
        call_command("send_mail_template", "missing", "alice@example.com")


@pytest.mark.django_db
def test_send_mail_template_command_unknown_applicant() -> None:
    MailTemplate.objects.create(
        name="Welcome",
        slug="welcome",
        subject="x",
        body="y",
    )
    with pytest.raises(CommandError, match="No Applicant"):
        call_command("send_mail_template", "welcome", "ghost@example.com")


def test_fetch_mail_command_errors_without_imap_host(settings) -> None:
    settings.IMAP_HOST = ""
    with pytest.raises(CommandError, match="IMAP_HOST is not configured"):
        call_command("fetch_mail")
