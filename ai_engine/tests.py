import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from complaints.models import Complaint
from .services import ComplaintClassifier


class ComplaintClassifierTests(SimpleTestCase):
    def test_classifier_labels_match_report_categories(self):
        classifier = ComplaintClassifier(model_path=Path(tempfile.gettempdir()) / "civiclens-test-model.joblib")

        self.assertEqual(
            set(classifier.label_map),
            {category for category, _ in Complaint.CATEGORY_CHOICES},
        )

    def test_training_evaluates_and_predicts_only_supported_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            classifier = ComplaintClassifier(model_path=Path(directory) / "model.joblib")
            metrics = classifier.train()
            prediction = classifier.predict("The traffic signal at the junction is broken.")

        self.assertIn("f1", metrics)
        self.assertIn(
            prediction["category"],
            {category for category, _ in Complaint.CATEGORY_CHOICES},
        )
