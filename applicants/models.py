"""Models for the applicants app.

This app models applicant-facing test sessions, including the assignment
of questions and the storage of responses. The :class:`Applicant` model
captures the minimum identity needed to correspond with the person
taking a test (name + email). Test, question, and response models are
introduced in follow-up issues.
"""

from __future__ import annotations

from django.db import models


class Applicant(models.Model):
    """A person who is invited to (or already taking) a test.

    The email address is the natural key used by the mail integration to
    route inbound messages back to the right applicant, so it is unique
    and required.
    """

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "email")

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
