"""Pull new mail from the configured IMAP mailbox and ingest it.

Usage::

    python manage.py fetch_mail
    python manage.py fetch_mail --limit 10
    python manage.py fetch_mail --no-mark-seen

The IMAP connection parameters come from settings (``IMAP_HOST``,
``IMAP_PORT``, ``IMAP_USERNAME``, ``IMAP_PASSWORD``, ``IMAP_USE_SSL``,
``IMAP_MAILBOX``) which in turn read from environment variables.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...services.fetcher import ingest_many
from ...services.imap_client import IMAPSettings, fetch_unseen


class Command(BaseCommand):
    help = "Fetch UNSEEN messages from IMAP and ingest them as inbound MailMessage rows."

    def add_arguments(self, parser) -> None:  # noqa: D401 - Django convention
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of messages to ingest in this run.",
        )
        parser.add_argument(
            "--no-mark-seen",
            dest="mark_seen",
            action="store_false",
            default=True,
            help="Do not mark fetched messages as Seen on the server.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        host = getattr(settings, "IMAP_HOST", "")
        if not host:
            raise CommandError(
                "IMAP_HOST is not configured. Set IMAP_HOST/IMAP_USERNAME/"
                "IMAP_PASSWORD (see .env.example) before running this command."
            )

        imap_settings = IMAPSettings(
            host=host,
            port=getattr(settings, "IMAP_PORT", 993),
            username=getattr(settings, "IMAP_USERNAME", ""),
            password=getattr(settings, "IMAP_PASSWORD", ""),
            use_ssl=getattr(settings, "IMAP_USE_SSL", True),
            mailbox=getattr(settings, "IMAP_MAILBOX", "INBOX"),
        )

        raws = fetch_unseen(
            imap_settings,
            mark_seen=options["mark_seen"],
            limit=options["limit"],
        )

        if not raws:
            self.stdout.write("No new messages.")
            return

        ingested = ingest_many(raws)
        self.stdout.write(
            self.style.SUCCESS(
                f"Fetched {len(raws)} message(s), ingested {len(ingested)} new row(s)."
            )
        )
