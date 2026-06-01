# Application Test Platform

A Django web application that lets **applicants** answer questions and submit
**predefined** and/or **free-text** responses, and lets **administrators**
author question banks, schedule tests, and review submissions.

The application exposes two clearly separated frontends:

| URL prefix     | Audience      | App              |
| -------------- | ------------- | ---------------- |
| `/`            | Applicants    | `applicants`     |
| `/manage/`     | Administrators| `administrative` |
| `/django-admin/` | Django staff | (built-in)       |

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
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── applicants/                # Django app: applicant-facing views
│   ├── migrations/
│   ├── templates/applicants/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
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

## License

This project is licensed under the Apache License, Version 2.0 — see
[`LICENSE.md`](LICENSE.md) for the full text.
