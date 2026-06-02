"""Send a mail template to an applicant from the CLI.

Example::

    python manage.py send_mail_template welcome alice@example.com
    python manage.py send_mail_template welcome alice@example.com --context '{"role": "Engineer"}'
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from applicants.models import Applicant

from ...models import MailTemplate
from ...services.sender import MailSendError, send_template_to_applicant


class Command(BaseCommand):
    help = "Render a MailTemplate and send it to an Applicant."

    def add_arguments(self, parser) -> None:  # noqa: D401 - Django convention
        parser.add_argument(
            "template_slug",
            help="Slug of the MailTemplate to send.",
        )
        parser.add_argument(
            "applicant_email",
            help="Email address of the Applicant to send to.",
        )
        parser.add_argument(
            "--context",
            help=(
                "Optional JSON object with extra template context "
                "(merged on top of the default {'applicant': ...} binding)."
            ),
            default=None,
        )
        parser.add_argument(
            "--from",
            dest="from_address",
            help="Override the From: address. Defaults to DEFAULT_FROM_EMAIL.",
            default=None,
        )

    def handle(self, *args: Any, **options: Any) -> None:
        slug = options["template_slug"]
        email = options["applicant_email"]

        try:
            template = MailTemplate.objects.get(slug=slug)
        except MailTemplate.DoesNotExist as exc:
            raise CommandError(f"No MailTemplate with slug {slug!r}") from exc

        try:
            applicant = Applicant.objects.get(email__iexact=email)
        except Applicant.DoesNotExist as exc:
            raise CommandError(f"No Applicant with email {email!r}") from exc

        context = None
        if options["context"]:
            try:
                context = json.loads(options["context"])
            except json.JSONDecodeError as exc:
                raise CommandError(f"--context is not valid JSON: {exc}") from exc
            if not isinstance(context, dict):
                raise CommandError("--context must decode to a JSON object")

        try:
            message = send_template_to_applicant(
                template=template,
                applicant=applicant,
                context=context,
                from_address=options["from_address"],
            )
        except MailSendError as exc:
            raise CommandError(f"Send failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent template '{template.slug}' to {applicant.email} "
                f"(MailMessage id={message.pk}, Message-ID={message.message_id})"
            )
        )
