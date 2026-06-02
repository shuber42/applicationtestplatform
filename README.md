# Application Test Platform

A Django web application that lets **applicants** answer questions and submit
**predefined** and/or **free-text** responses, and lets **administrators**
author question banks, schedule tests, send mail to applicants, and review
submissions.

The application exposes two clearly separated frontends:

| URL prefix     | Audience      | App              |
| -------------- | ------------- | ---------------- |
| `/`            | Applicants    | `applicants`     |
| `/manage/`     | Administrators| `administrative` |
| `/django-admin/` | Django staff | (built-in)       |

A dedicated `mailroom` app handles all mail traffic — outbound sends through
Django's `EMAIL_BACKEND` and inbound ingest from IMAP via the
`fetch_mail` management command.

## Project structure

```
applicationtestplatform/
├── applicationtestplatform/   # Django project package
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── administrative/            # Django app: administrator-facing views
│   ├── migrations/
│   ├── templates/administrative/
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── applicants/                # Django app: applicant-facing views + Applicant model
│   ├── migrations/
│   ├── templates/applicants/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── mailroom/                  # Django app: mail templates + send/receive
│   ├── management/commands/   # send_mail_template, fetch_mail
│   ├── migrations/
│   ├── services/              # sender, fetcher (parser), imap_client
│   ├── admin.py
│   ├── apps.py
│   ├── models.py              # MailTemplate, MailMessage
│   └── tests.py
├── static/                    # Project-wide static assets
│   └── css/site.css
├── templates/                 # Project-wide templates
│   └── base.html
├── docs/
├── scripts/
├── .github/workflows/         # CI pipelines
│   └── ci.yml
├── .env.example               # Sample environment variables
├── .gitignore
├── CHANGELOG.md
├── LICENSE.md                 # Apache 2.0
├── Makefile                   # Common dev commands
├── manage.py
├── MANIFEST.in
├── pyproject.toml             # Project metadata, pytest & ruff config
├── README.md
├── requirements.txt           # Runtime dependencies
└── requirements-dev.txt       # Test/lint dependencies
```

## Getting started

### Prerequisites

* Python 3.11 or newer
* `pip`

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/shuber42/applicationtestplatform.git
cd applicationtestplatform

# 2. (Recommended) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
make install-dev          # or: pip install -r requirements-dev.txt

# 4. Copy the environment template and edit it
cp .env.example .env

# 5. Apply database migrations
make migrate              # or: python manage.py migrate

# 6. Create a staff user for the administrative app
python manage.py createsuperuser

# 7. Start the development server
make runserver            # or: python manage.py runserver
```

Then open:

* <http://127.0.0.1:8000/> — the applicant-facing landing page
* <http://127.0.0.1:8000/manage/> — the administrative dashboard
  (requires login)
* <http://127.0.0.1:8000/django-admin/> — Django's built-in admin

## Development

Common tasks are exposed via the `Makefile`:

| Command          | What it does                          |
| ---------------- | ------------------------------------- |
| `make install`   | Install runtime dependencies          |
| `make install-dev` | Install runtime + dev dependencies  |
| `make migrate`   | Apply database migrations             |
| `make runserver` | Start the Django dev server           |
| `make test`      | Run the test suite (pytest)           |
| `make lint`      | Lint the codebase (ruff)              |
| `make format`    | Auto-format the codebase (ruff)       |
| `make check`     | Run Django's system checks            |
| `make clean`     | Remove build / cache artifacts        |

## Mail integration

Outbound and inbound mail are handled by the `mailroom` app.

* **Templates.** Author re-usable `MailTemplate` records in
  `/manage/mail/templates/` or the Django admin. Subject and body use
  the Django template engine, so you can write things like
  `Hello {{ applicant.name }}` and the template is rendered against the
  addressed applicant at send time.
* **Sending.** From the administrative UI, pick a template and an
  applicant on `/manage/mail/send/`. From the CLI, run
  `python manage.py send_mail_template <slug> <applicant-email>`. Both
  paths persist a `MailMessage` audit row and use Django's
  `EMAIL_BACKEND` for transport.
* **Receiving.** Configure the `IMAP_*` env vars from
  [`.env.example`](.env.example) and run `python manage.py fetch_mail`
  (typically on a cron / systemd timer). The command pulls UNSEEN
  messages, parses them, links them back to applicants by `From:`
  address, and stores them as inbound `MailMessage` rows.
* **History.** `/manage/mail/messages/` lists every sent and received
  message. Each applicant detail page (`/manage/applicants/<id>/`)
  shows the per-applicant thread.

When `DJANGO_DEBUG=1` the outbound backend defaults to
`django.core.mail.backends.console.EmailBackend`, so a fresh checkout
can render and "send" mail without an SMTP server.

## License

This project is licensed under the Apache License, Version 2.0 — see
[`LICENSE.md`](LICENSE.md) for the full text.
