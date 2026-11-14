from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from complaints.forms import ComplaintForm
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

    def test_ai_prediction_rejects_anonymous_requests(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/ai/predict/", {"text": "Water leak near the road."}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_ai_prediction_does_not_return_other_residents_reports(self):
        other_user = User.objects.create_user(username="other-citizen", password="SafePass!12345")
        Complaint.objects.create(
            user=other_user,
            title="Private water supply report",
            description="Water supply stopped in the neighborhood.",
            category="WATER_SUPPLY",
        )
        response = self.client.post(
            "/api/ai/predict/",
            {"text": "Water supply stopped in the neighborhood."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["similar_reports"], [])

    def test_ai_prediction_accepts_new_category_labels(self):
        response = self.client.post(
            "/api/ai/predict/",
            {"text": "The traffic signal at the junction is broken and dangerous."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            response.data["prediction"]["category"],
            {choice[0] for choice in Complaint.CATEGORY_CHOICES},
        )

    @override_settings(MEDIA_UPLOADS_ENABLED=False)
    def test_complaint_form_hides_photo_upload_without_media_storage(self):
        self.assertNotIn("image", ComplaintForm().fields)

    @override_settings(MEDIA_UPLOADS_ENABLED=False)
    def test_api_rejects_photo_upload_without_media_storage(self):
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="JPEG")
        response = self.client.post(
            "/api/complaints/",
            {
                "title": "Blocked drain",
                "description": "Water is pooling around a blocked drain.",
                "category": "WATER",
                "image": SimpleUploadedFile(
                    "evidence.jpg", image_buffer.getvalue(), content_type="image/jpeg"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)
