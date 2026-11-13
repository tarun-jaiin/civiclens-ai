from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from complaints.models import Complaint


class CivicLensApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="citizen", password="StrongPass123")
        self.client.force_authenticate(user=self.user)

    def test_register_endpoint_creates_user_and_returns_token(self):
        client = APIClient()
        response = client.post(
            "/api/auth/register/",
            {"username": "newuser", "email": "new@example.com", "password": "StrongPass!123"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.data)

    def test_complaint_reference_number_is_generated(self):
        complaint = Complaint.objects.create(
            user=self.user,
            title="Road damage",
            description="Pothole on main road.",
            category="ROAD_DAMAGE",
        )
        self.assertTrue(complaint.reference_number.startswith("CL-"))

    def test_ai_prediction_endpoint_returns_prediction(self):
        response = self.client.post("/api/ai/predict/", {"text": "Water leak causing flooding on the road."}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("prediction", response.data)
        self.assertIn("category", response.data["prediction"])
