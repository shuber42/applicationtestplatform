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
