from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from complaints.models import Complaint, ComplaintHistory
from complaints.sla import breached_complaints, get_sla_deadline, is_sla_breached


class RoleSpecificWorkspaceTests(TestCase):
    def setUp(self):
        self.citizen = User.objects.create_user(
            username="resident",
            password="Resident-Testing-123!",
        )
        self.staff = User.objects.create_user(
            username="city-staff",
            password="Staff-Testing-123!",
            is_staff=True,
        )
        self.report = Complaint.objects.create(
            user=self.citizen,
            title="Streetlight out",
            description="The streetlight is not working near the library.",
            category="STREETLIGHT",
            latitude="19.076000",
            longitude="72.877700",
        )

    def test_public_home_has_distinct_resident_and_staff_entry_points(self):
        response = self.client.get(reverse("homepage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/register/"')
        self.assertContains(response, 'href="/login/"')

    def test_sign_in_routes_each_role_to_its_own_workspace(self):
        citizen_response = self.client.post(
            reverse("web-login"),
            {"username": self.citizen.username, "password": "Resident-Testing-123!"},
        )
        self.assertRedirects(
            citizen_response,
            reverse("citizen-dashboard"),
            fetch_redirect_response=False,
        )
        self.client.logout()

        staff_response = self.client.post(
            reverse("web-login"),
            {"username": self.staff.username, "password": "Staff-Testing-123!"},
        )
        self.assertRedirects(
            staff_response,
            reverse("admin-dashboard"),
            fetch_redirect_response=False,
        )

    def test_public_registration_creates_a_citizen_not_staff(self):
        response = self.client.post(
            reverse("resident-register"),
            {
                "username": "new-resident",
                "password1": "Resident-Testing-789!",
                "password2": "Resident-Testing-789!",
                "is_staff": "on",
            },
        )

        new_user = User.objects.get(username="new-resident")
        self.assertRedirects(
            response,
            reverse("citizen-dashboard"),
            fetch_redirect_response=False,
        )
        self.assertFalse(new_user.is_staff)

    def test_citizen_routes_to_citizen_workspace_and_only_sees_own_reports(self):
        other_citizen = User.objects.create_user(
            username="another-resident",
            password="Resident-Testing-456!",
        )
        other_report = Complaint.objects.create(
            user=other_citizen,
            title="Other resident's report",
            description="This must remain private to its owner.",
        )
        self.client.force_login(self.citizen)

        response = self.client.get(reverse("citizen-dashboard"))
        detail_response = self.client.get(
            reverse("report-detail", args=[other_report.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.report.title)
        self.assertNotContains(response, other_report.title)
        self.assertRedirects(
            detail_response,
            reverse("citizen-dashboard"),
            fetch_redirect_response=False,
        )

    def test_staff_routes_to_citywide_dashboard_and_can_update_status(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin-dashboard"))
        update_response = self.client.post(
            reverse("complaint-status-update", args=[self.report.pk]),
            {"status": "IN_PROGRESS"},
        )

        self.report.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.report.title)
        self.assertRedirects(update_response, reverse("admin-dashboard"))
        self.assertEqual(self.report.status, "IN_PROGRESS")

    def test_staff_report_detail_shows_history_and_assignment_controls(self):
        ComplaintHistory.objects.create(
            complaint=self.report,
            actor=self.staff,
            event_type="CREATED",
            new_value="SUBMITTED",
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("report-detail", args=[self.report.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Updates and actions")
        self.assertContains(response, 'name="assigned_to"')
        self.assertContains(response, "Report created")

    def test_staff_can_assign_department_and_owner_with_audit_events(self):
        self.client.force_login(self.staff)
        assignee = User.objects.create_user(
            username="road-operator",
            password="Operator-Testing-123!",
            is_staff=True,
        )

        response = self.client.post(
            reverse("complaint-status-update", args=[self.report.pk]),
            {
                "status": "UNDER_REVIEW",
                "priority": "HIGH",
                "department": "ROADS",
                "assigned_to": assignee.pk,
            },
        )

        self.report.refresh_from_db()
        self.assertRedirects(response, reverse("admin-dashboard"))
        self.assertEqual(self.report.department, "ROADS")
        self.assertEqual(self.report.assigned_to, assignee)
        self.assertEqual(self.report.status, "UNDER_REVIEW")
        self.assertEqual(
            self.report.history.filter(event_type="ASSIGNMENT").count(), 2
        )
        self.assertTrue(self.report.history.filter(event_type="STATUS").exists())
        self.assertTrue(self.report.history.filter(event_type="PRIORITY").exists())

    def test_only_report_owner_can_leave_feedback_after_resolution(self):
        self.report.status = "RESOLVED"
        self.report.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.citizen)

        detail_response = self.client.get(
            reverse("report-detail", args=[self.report.pk])
        )
        response = self.client.post(
            reverse("complaint-feedback", args=[self.report.pk]),
            {"resolution_rating": "5", "resolution_feedback": "Fixed quickly."},
        )

        self.report.refresh_from_db()
        self.assertRedirects(
            response, reverse("report-detail", args=[self.report.pk])
        )
        self.assertContains(detail_response, "How did we do?")
        self.assertEqual(self.report.resolution_rating, 5)
        self.assertEqual(self.report.resolution_feedback, "Fixed quickly.")
        self.assertTrue(self.report.history.filter(event_type="FEEDBACK").exists())

    def test_unresolved_or_non_owner_feedback_is_not_saved(self):
        self.client.force_login(self.citizen)
        response = self.client.post(
            reverse("complaint-feedback", args=[self.report.pk]),
            {"resolution_rating": "4", "resolution_feedback": "Premature"},
        )

        self.report.refresh_from_db()
        self.assertRedirects(
            response, reverse("report-detail", args=[self.report.pk])
        )
        self.assertIsNone(self.report.resolution_rating)
        self.assertFalse(self.report.history.filter(event_type="FEEDBACK").exists())

        self.report.status = "RESOLVED"
        self.report.save(update_fields=["status", "updated_at"])
        other_citizen = User.objects.create_user(
            username="other-owner",
            password="Other-Testing-123!",
        )
        self.client.force_login(other_citizen)
        response = self.client.post(
            reverse("complaint-feedback", args=[self.report.pk]),
            {"resolution_rating": "4"},
        )
        self.assertEqual(response.status_code, 404)

    def test_sla_targets_and_breached_report_query(self):
        now = timezone.now()
        self.assertEqual(
            get_sla_deadline(now, "CRITICAL") - now,
            timedelta(hours=4),
        )
        self.report.created_at = now - timedelta(days=8)
        self.report.save(update_fields=["created_at"])

        self.assertTrue(is_sla_breached(self.report, now=now))
        self.assertTrue(breached_complaints(Complaint.objects.all(), now=now).exists())
        self.report.status = "RESOLVED"
        self.assertFalse(is_sla_breached(self.report, now=now))

    def test_citizen_cannot_access_staff_dashboard_or_update_status(self):
        self.client.force_login(self.citizen)

        dashboard_response = self.client.get(reverse("admin-dashboard"))
        update_response = self.client.post(
            reverse("complaint-status-update", args=[self.report.pk]),
            {"status": "RESOLVED"},
        )

        self.report.refresh_from_db()
        self.assertRedirects(
            dashboard_response,
            reverse("citizen-dashboard"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            update_response,
            reverse("citizen-dashboard"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.report.status, "SUBMITTED")

    def test_citizen_portal_creates_a_report_with_selected_location(self):
        self.client.force_login(self.citizen)

        response = self.client.post(
            reverse("citizen-dashboard"),
            {
                "title": "Blocked drain",
                "description": "A drain is blocked outside the community hall.",
                "category": "DRAINAGE",
                "latitude": "19.080000",
                "longitude": "72.880000",
            },
        )

        created = Complaint.objects.get(title="Blocked drain")
        self.assertRedirects(response, reverse("citizen-dashboard"))
        self.assertEqual(created.user, self.citizen)
        self.assertEqual(str(created.latitude), "19.080000")
        self.assertEqual(str(created.longitude), "72.880000")

    def test_staff_dashboard_contains_live_chart_data_and_map_pin(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin-dashboard"))

        self.assertContains(response, 'id="admin-map-data"')
        self.assertContains(response, 'id="category-chart-data"')
        self.assertContains(response, '"latitude": "19.076000"')
        self.assertContains(response, "Workload by department")
        self.assertContains(response, "SLA overdue")

    def test_citizen_cannot_change_report_status_through_the_api(self):
        client = APIClient()
        client.force_authenticate(user=self.citizen)

        response = client.patch(
            f"/api/complaints/{self.report.pk}/",
            {"status": "RESOLVED"},
            format="json",
        )

        self.report.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.report.status, "SUBMITTED")

    def test_dashboard_api_requires_staff_access(self):
        client = APIClient()
        self.assertEqual(client.get("/api/analytics/dashboard/").status_code, 401)
        client.force_authenticate(user=self.citizen)
        self.assertEqual(client.get("/api/analytics/dashboard/").status_code, 403)
        client.force_authenticate(user=self.staff)
        self.assertEqual(client.get("/api/analytics/dashboard/").status_code, 200)

    def test_health_endpoint_reports_database_status(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_api_schema_is_available(self):
        response = self.client.get(reverse("openapi-schema"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"openapi", response.content.lower())

    def test_authenticated_workspaces_include_quick_guide(self):
        self.client.force_login(self.citizen)
        response = self.client.get(reverse("citizen-dashboard"))
        self.assertContains(response, "CIVICLENS QUICK GUIDE")
        self.assertContains(response, 'id="guide-dialog"')
