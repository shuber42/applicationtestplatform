"""URL configuration for the applicationtestplatform project.

The project exposes two distinct frontends:

* ``/django-admin/`` - Django's built-in staff-facing admin site
* ``/manage/``       - the project-specific ``administrative`` app
* ``/``              - the applicant-facing ``applicants`` app
"""

from django.contrib import admin
from django.urls import include, path

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path(settings.ADMIN_SITE_URL, admin.site.urls),
    path(settings.ADMINISTRATIVE_URL_PREFIX, include("administrative.urls")),
    path(settings.APPLICANTS_URL_PREFIX, include("applicants.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
