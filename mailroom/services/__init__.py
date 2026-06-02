"""Service modules for the mailroom app.

Each module is a thin, dependency-injectable wrapper around a single
concern so it can be exercised in tests without touching real SMTP/IMAP
servers.
"""
