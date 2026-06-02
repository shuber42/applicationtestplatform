# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial Django project skeleton with separate `administrative` and `applicants` apps
- `README.md` with project overview and quickstart
- `LICENSE.md` (Apache 2.0)
- `pyproject.toml` with project metadata, pytest and ruff configuration
- `requirements.txt` and `requirements-dev.txt`
- `.env.example` and `.gitignore`
- `Makefile` with common development commands
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- Smoke tests for both apps
- Base template and minimal landing pages for the administrative and applicant frontends
- `Applicant` model with admin registration and migration
- New `mailroom` Django app providing:
  - `MailTemplate` model with Django-template rendering (`{{ applicant.name }}` etc.)
  - `MailMessage` audit model for inbound and outbound mail
  - `send_template_to_applicant` service backed by `django.core.mail`
  - `parse_inbound` / `ingest_inbound_message` parser for raw RFC 5322 bytes
  - `imap_client` minimal IMAP transport (stdlib `imaplib`)
  - `send_mail_template` and `fetch_mail` management commands
  - Django admin registrations for `MailTemplate` and `MailMessage`
- Staff-only administrative views for applicants, mail templates, sending mail,
  and reviewing inbound/outbound mail history
- Env-driven SMTP outbound (console backend default in DEBUG) and IMAP inbound
  configuration, documented in `.env.example`
