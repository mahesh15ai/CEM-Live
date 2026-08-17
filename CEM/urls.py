from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import include, path


# ⚡ 1. Ultra-lightweight Ping Endpoint (Zero DB overhead)
def ping_view(request):
  return HttpResponse("pong", content_type="text/plain")


urlpatterns = [
    # Keep-Alive Route for Free Uptime Cron
    path("api/ping/", ping_view, name="ping"),
    # Root Redirect
    path("", lambda request: redirect("/accounts/login/")),
    path("admin/", admin.site.urls),
    # 📌 Custom Password Reset Flow (Forces your custom templates)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # Accounts & Application Apps
    path("accounts/", include("accounts.urls")),
    path("students/", include("students.urls")),
    path("teachers/", include("teachers.urls")),
    path("attendance/", include("attendance.urls")),
    path("events/", include("events.urls")),
    path("certificates/", include("certificates.urls")),
]

# 📌 Serve local media & static files ONLY during local development
if settings.DEBUG:
  urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
  urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)