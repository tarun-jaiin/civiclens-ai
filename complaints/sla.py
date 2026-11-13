from datetime import timedelta

from django.db.models import Q
from django.utils import timezone


# Prototype SLA targets only; a real municipality must configure its own policy.
SLA_HOURS = {
    "CRITICAL": 4,
    "HIGH": 24,
    "MEDIUM": 72,
    "LOW": 168,
}


def get_sla_deadline(created_at, priority):
    return created_at + timedelta(hours=SLA_HOURS.get(priority, SLA_HOURS["MEDIUM"]))


def is_sla_breached(complaint, now=None):
    if complaint.status in {"RESOLVED", "REJECTED"}:
        return False
    return (now or timezone.now()) > get_sla_deadline(
        complaint.created_at, complaint.priority
    )


def breached_complaints(queryset, now=None):
    current_time = now or timezone.now()
    overdue = Q(pk__in=[])
    for priority, hours in SLA_HOURS.items():
        overdue |= Q(
            priority=priority,
            created_at__lt=current_time - timedelta(hours=hours),
        )
    return queryset.exclude(status__in=["RESOLVED", "REJECTED"]).filter(overdue)
