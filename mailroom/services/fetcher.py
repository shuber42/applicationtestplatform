"""Inbound mail ingestion service.

Parses raw RFC 5322 messages (as produced by an IMAP fetch) into
:class:`MailMessage` rows. The IMAP transport itself lives in
:mod:`mailroom.services.imap_client`; this module is pure-Python and
unit-testable without a network connection.

The main entry point is :func:`ingest_inbound_message`, which:

1. Parses the message with the stdlib :mod:`email` package.
2. Extracts envelope, body, ``Message-ID``, ``In-Reply-To``.
3. Skips messages whose ``Message-ID`` we have already stored.
4. Links the message to an :class:`Applicant` by ``From:`` address.
5. Persists a :class:`MailMessage` row with ``direction=in``.
"""

from __future__ import annotations

import email
import logging
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from email import policy
from email.message import EmailMessage as StdlibEmailMessage
from email.utils import getaddresses, parsedate_to_datetime

from django.db import transaction
from django.utils import timezone

from applicants.models import Applicant

from ..models import MailMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedInboundMessage:
    """Pure-data view of a parsed inbound message (no DB)."""

    from_address: str
    to_address: str
    subject: str
    body: str
    message_id: str
    in_reply_to: str
    received_at: datetime | None


def _first_address(values: list[str]) -> str:
    """Return the first email address in a list of header values."""

    pairs = getaddresses([v for v in values if v])
    for _, addr in pairs:
        if addr:
            return addr.strip()
    return ""


def _extract_text_body(msg: StdlibEmailMessage) -> str:
    """Return the best-effort plain-text body of ``msg``.

    Prefers ``text/plain`` parts. Falls back to ``text/html`` stripped
    of tags only as a last resort, keeping the output simple enough for
    review in the administrative UI.
    """

    if msg.is_multipart():
        plain = msg.get_body(preferencelist=("plain",))
        if plain is not None:
            return plain.get_content().rstrip("\n")
        html = msg.get_body(preferencelist=("html",))
        if html is not None:
            return _strip_html(html.get_content())
        return ""
    content_type = msg.get_content_type()
    if content_type == "text/plain":
        return msg.get_content().rstrip("\n")
    if content_type == "text/html":
        return _strip_html(msg.get_content())
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _strip_html(value: str) -> str:
    """Very small HTML-to-text helper, intentionally minimal."""

    import re

    text = re.sub(r"<\s*br\s*/?\s*>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</\s*p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def parse_inbound(raw: bytes | str) -> ParsedInboundMessage:
    """Parse a raw RFC 5322 message into a :class:`ParsedInboundMessage`."""

    if isinstance(raw, str):
        raw_bytes = raw.encode("utf-8", errors="replace")
    else:
        raw_bytes = raw

    msg: StdlibEmailMessage = email.message_from_bytes(  # type: ignore[assignment]
        raw_bytes, policy=policy.default
    )

    from_address = _first_address(msg.get_all("From", []))
    to_address = _first_address(msg.get_all("To", []))
    subject = (msg.get("Subject") or "").strip()
    body = _extract_text_body(msg).strip()
    message_id = (msg.get("Message-ID") or "").strip().strip("<>")
    in_reply_to = (msg.get("In-Reply-To") or "").strip().strip("<>")

    received_at: datetime | None = None
    date_header = msg.get("Date")
    if date_header:
        try:
            received_at = parsedate_to_datetime(date_header)
        except (TypeError, ValueError):
            received_at = None
    if received_at and received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=dt_timezone.utc)

    return ParsedInboundMessage(
        from_address=from_address,
        to_address=to_address,
        subject=subject,
        body=body,
        message_id=message_id,
        in_reply_to=in_reply_to,
        received_at=received_at,
    )


def _match_applicant(parsed: ParsedInboundMessage) -> Applicant | None:
    if not parsed.from_address:
        return None
    return Applicant.objects.filter(email__iexact=parsed.from_address).first()


@transaction.atomic
def ingest_inbound_message(raw: bytes | str) -> MailMessage | None:
    """Persist a single inbound message.

    Returns the created :class:`MailMessage`, or ``None`` if the message
    is a duplicate (already stored under the same Message-ID with
    ``direction=in``).
    """

    parsed = parse_inbound(raw)

    if parsed.message_id:
        existing = MailMessage.objects.filter(
            direction=MailMessage.DIRECTION_INBOUND,
            message_id=parsed.message_id,
        ).first()
        if existing is not None:
            logger.info(
                "Skipping duplicate inbound message (message-id=%s)",
                parsed.message_id,
            )
            return None

    applicant = _match_applicant(parsed)
    raw_text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw

    message = MailMessage.objects.create(
        direction=MailMessage.DIRECTION_INBOUND,
        status=MailMessage.STATUS_RECEIVED,
        applicant=applicant,
        from_address=parsed.from_address or "unknown@invalid",
        to_address=parsed.to_address or "",
        subject=parsed.subject,
        body=parsed.body,
        message_id=parsed.message_id,
        in_reply_to=parsed.in_reply_to,
        received_at=parsed.received_at or timezone.now(),
        raw=raw_text,
    )
    logger.info(
        "Ingested inbound message from %s (applicant=%s, message-id=%s)",
        parsed.from_address,
        applicant.pk if applicant else None,
        parsed.message_id,
    )
    return message


def ingest_many(raw_messages) -> list[MailMessage]:
    """Ingest an iterable of raw messages, returning the new rows."""

    ingested: list[MailMessage] = []
    for raw in raw_messages:
        try:
            row = ingest_inbound_message(raw)
        except Exception:
            logger.exception("Failed to ingest inbound message")
            continue
        if row is not None:
            ingested.append(row)
    return ingested
