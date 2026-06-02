"""Outbound mail sending service.

The single entry point :func:`send_template_to_applicant` renders a
:class:`MailTemplate` against an :class:`Applicant`, stores a
:class:`MailMessage` audit row, and delegates the actual transport to
Django's :mod:`django.core.mail` (which respects ``EMAIL_BACKEND``).

The Django email backend is injected via :class:`EmailMessage` so this
service stays unit-testable with :mod:`django.core.mail.outbox` and so
operators can swap SMTP for the console backend in development without
touching the service.
"""

from __future__ import annotations

import logging
import uuid
from email.utils import formataddr, make_msgid

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.db import transaction
from django.utils import timezone

from applicants.models import Applicant

from ..models import MailMessage, MailTemplate

logger = logging.getLogger(__name__)


class MailSendError(RuntimeError):
    """Raised when the underlying mail backend refuses a message."""


def _default_from_address() -> str:
    return getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost") or "webmaster@localhost"


def _generate_message_id() -> str:
    """Return a brand-new RFC 5322 Message-ID without angle brackets."""

    # ``make_msgid`` returns ``<token@domain>`` — strip the brackets so
    # the value stored in the database matches the way we look it up
    # later (callers compare bare Message-IDs).
    domain = getattr(settings, "MAIL_MESSAGE_ID_DOMAIN", None)
    raw = make_msgid(idstring=uuid.uuid4().hex, domain=domain) if domain else make_msgid(idstring=uuid.uuid4().hex)
    return raw.strip("<>")


@transaction.atomic
def send_template_to_applicant(
    *,
    template: MailTemplate,
    applicant: Applicant,
    context: dict | None = None,
    from_address: str | None = None,
    reply_to: list[str] | None = None,
    connection=None,
) -> MailMessage:
    """Render ``template`` for ``applicant`` and send it.

    Returns the persisted :class:`MailMessage` (already marked ``sent``
    on success). Raises :class:`MailSendError` if the backend refuses
    the message; the audit row is still written with ``status=failed``
    and ``error`` populated so a follow-up retry can find it.
    """

    if not template.is_active:
        raise MailSendError(f"Template {template.slug!r} is not active")

    subject, body = template.render(applicant=applicant, context=context)
    sender = from_address or _default_from_address()
    recipient = applicant.email
    message_id = _generate_message_id()

    message = MailMessage.objects.create(
        direction=MailMessage.DIRECTION_OUTBOUND,
        status=MailMessage.STATUS_PENDING,
        applicant=applicant,
        template=template,
        from_address=sender,
        to_address=recipient,
        subject=subject,
        body=body,
        message_id=message_id,
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=formataddr((None, sender)) if "<" not in sender else sender,
        to=[formataddr((applicant.name, recipient))],
        reply_to=reply_to or None,
        headers={"Message-ID": f"<{message_id}>"},
        connection=connection or get_connection(),
    )

    try:
        sent_count = email.send(fail_silently=False)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to send mail to %s", recipient)
        message.mark_failed(str(exc))
        raise MailSendError(str(exc)) from exc

    if not sent_count:
        message.mark_failed("Backend reported zero messages sent")
        raise MailSendError("Backend reported zero messages sent")

    message.mark_sent(when=timezone.now())
    logger.info(
        "Sent template '%s' to applicant %s (message-id=%s)",
        template.slug,
        applicant.pk,
        message_id,
    )
    return message
