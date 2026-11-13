"""URL configuration for config project."""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from analytics import views as analytics_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", analytics_views.homepage, name="homepage"),
    path("login/", analytics_views.login_view, name="web-login"),
    path("logout/", analytics_views.logout_view, name="logout"),
    path("register/", analytics_views.register_view, name="resident-register"),
    path("citizen/", analytics_views.citizen_dashboard, name="citizen-dashboard"),
    path("complaint/<int:pk>/", analytics_views.complaint_detail, name="report-detail"),
    path(
        "complaint/<int:pk>/status/",
        analytics_views.update_complaint_status,
        name="complaint-status-update",
    ),
    path(
        "complaint/<int:pk>/feedback/",
        analytics_views.submit_resolution_feedback,
        name="complaint-feedback",
    ),
    path("dashboard/", analytics_views.admin_dashboard, name="admin-dashboard"),
    path("assistant/", analytics_views.knowledge_assistant, name="ai-assistant"),
    path("api/auth/", include("accounts.urls")),
    path("api/complaints/", include("complaints.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/ai/", include("ai_engine.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
