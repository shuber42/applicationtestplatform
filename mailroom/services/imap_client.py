"""Thin IMAP transport used by :mod:`mailroom.services.fetcher`.

The goal is to keep IMAP-specific quirks out of the parser so the
parser can be tested with raw bytes only. This module is intentionally
minimal: connect, select a mailbox, yield ``UNSEEN`` (or ``ALL``)
messages, optionally mark them seen.
"""

from __future__ import annotations

import imaplib
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IMAPSettings:
    """Connection parameters for an IMAP mailbox."""

    host: str
    port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    mailbox: str = "INBOX"


def _connect(settings: IMAPSettings) -> imaplib.IMAP4:
    if settings.use_ssl:
        client: imaplib.IMAP4 = imaplib.IMAP4_SSL(settings.host, settings.port)
    else:
        client = imaplib.IMAP4(settings.host, settings.port)
    if settings.username:
        client.login(settings.username, settings.password)
    return client


@contextmanager
def imap_session(settings: IMAPSettings) -> Iterator[imaplib.IMAP4]:
    """Context manager yielding a logged-in IMAP client."""

    client = _connect(settings)
    try:
        yield client
    finally:
        try:
            client.logout()
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to cleanly close IMAP session")


def fetch_unseen(
    settings: IMAPSettings,
    *,
    mark_seen: bool = True,
    limit: int | None = None,
) -> list[bytes]:
    """Return the raw RFC 5322 bytes of every UNSEEN message in ``mailbox``.

    Messages are read in arrival order; pass ``limit`` to cap how many
    are pulled in a single run. When ``mark_seen`` is ``True`` (the
    default) the messages are flagged ``\\Seen`` after a successful
    fetch so the next run does not see them again.
    """

    raws: list[bytes] = []
    with imap_session(settings) as client:
        typ, _ = client.select(settings.mailbox, readonly=False)
        if typ != "OK":
            raise RuntimeError(f"IMAP SELECT {settings.mailbox!r} failed: {typ}")

        typ, data = client.search(None, "UNSEEN")
        if typ != "OK":
            raise RuntimeError(f"IMAP SEARCH failed: {typ}")

        message_ids = data[0].split() if data and data[0] else []
        if limit is not None:
            message_ids = message_ids[:limit]

        for msg_id in message_ids:
            typ, msg_data = client.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not msg_data:
                logger.warning("IMAP FETCH %r failed: %s", msg_id, typ)
                continue
            for part in msg_data:
                if isinstance(part, tuple) and len(part) >= 2:
                    raws.append(part[1])
                    break
            if mark_seen:
                client.store(msg_id, "+FLAGS", r"(\Seen)")

    return raws
