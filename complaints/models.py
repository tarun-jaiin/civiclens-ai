import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .sla import is_sla_breached


class Complaint(models.Model):
    CATEGORY_CHOICES = [
        ("ROAD_DAMAGE", "Road Damage"),
        ("GARBAGE", "Garbage"),
        ("WATER_LEAKAGE", "Water Leakage"),
        ("WATER_SUPPLY", "Water Supply"),
        ("STREETLIGHT", "Streetlight"),
        ("TRAFFIC_SIGNALS", "Traffic Signals"),
        ("DRAINAGE", "Drainage"),
        ("PUBLIC_SAFETY", "Public Safety"),
        ("OTHER", "Other"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]

    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("REJECTED", "Rejected"),
    ]
    DEPARTMENT_CHOICES = [
        ("ROADS", "Road Maintenance"),
        ("WASTE", "Waste Operations"),
        ("WATER", "Water Utility"),
        ("LIGHTING", "Street Lighting"),
        ("DRAINAGE", "Drainage Division"),
        ("GENERAL", "General Services"),
    ]

    complaint_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="OTHER")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="MEDIUM")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUBMITTED")
    department = models.CharField(
        max_length=20, choices=DEPARTMENT_CHOICES, default="GENERAL"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assigned_complaints",
        null=True,
        blank=True,
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    image = models.ImageField(upload_to="complaints/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolution_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    resolution_feedback = models.TextField(blank=True)

    @property
    def reference_number(self):
        return f"CL-{self.complaint_id.hex[:8].upper()}"

    @property
    def is_sla_breached(self):
        return is_sla_breached(self)

    @property
    def sla_deadline(self):
        from .sla import get_sla_deadline

        return get_sla_deadline(self.created_at, self.priority)

    def __str__(self):
        return self.title


class ComplaintHistory(models.Model):
    EVENT_CHOICES = [
        ("CREATED", "Report created"),
        ("STATUS", "Status changed"),
        ("PRIORITY", "Priority changed"),
        ("ASSIGNMENT", "Assignment changed"),
        ("FEEDBACK", "Resolution feedback"),
        ("UPDATED", "Report edited"),
    ]

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="history"
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="civic_report_events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    old_value = models.CharField(max_length=200, blank=True)
    new_value = models.CharField(max_length=200, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.get_event_type_display()} · {self.complaint.reference_number}"
