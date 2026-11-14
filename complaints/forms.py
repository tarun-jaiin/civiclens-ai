from django import forms
from django.conf import settings

from .models import Complaint


class ComplaintForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.MEDIA_UPLOADS_ENABLED:
            self.fields.pop("image")

    class Meta:
        model = Complaint
        fields = ["title", "description", "category", "latitude", "longitude", "image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Broken water pipe near community center"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Describe the civic issue in detail"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "19.0760"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "72.8777"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")
        if (latitude is None) != (longitude is None):
            self.add_error("latitude", "Choose a point on the map so both coordinates are set.")
        if latitude is not None and not -90 <= latitude <= 90:
            self.add_error("latitude", "Latitude must be between -90 and 90.")
        if longitude is not None and not -180 <= longitude <= 180:
            self.add_error("longitude", "Longitude must be between -180 and 180.")
        return cleaned_data


class ResolutionFeedbackForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["resolution_rating", "resolution_feedback"]
        widgets = {
            "resolution_rating": forms.Select(
                choices=[
                    ("", "Select a rating"),
                    (1, "1 — Needs improvement"),
                    (2, "2 — Fair"),
                    (3, "3 — Good"),
                    (4, "4 — Very good"),
                    (5, "5 — Excellent"),
                ],
                attrs={"class": "form-select"},
            ),
            "resolution_feedback": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional: tell us how the resolution went.",
                }
            ),
        }

    def clean_resolution_rating(self):
        rating = self.cleaned_data.get("resolution_rating")
        if rating is not None and not 1 <= rating <= 5:
            raise forms.ValidationError("Choose a rating from 1 to 5.")
        return rating
