from collections import Counter

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from django.db.models import Avg, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ai_engine.services import ComplaintClassifier
from complaints.forms import ComplaintForm, ResolutionFeedbackForm
from complaints.models import Complaint, ComplaintHistory
from complaints.sla import breached_complaints


def _dashboard_for(user):
    return "admin-dashboard" if user.is_staff else "citizen-dashboard"


def homepage(request):
    return render(request, "landing.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_for(request.user))

    form = UserCreationForm(request.POST or None)
    for field in form.fields.values():
        field.widget.attrs["class"] = "form-control"
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your citizen account is ready.")
        return redirect("citizen-dashboard")
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_for(request.user))

    form = AuthenticationForm(request, data=request.POST or None)
    for field in form.fields.values():
        field.widget.attrs["class"] = "form-control"
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect(_dashboard_for(user))
    return render(request, "login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("homepage")


@login_required(login_url="/login/")
def citizen_dashboard(request):
    if request.user.is_staff:
        return redirect("admin-dashboard")

    complaints = Complaint.objects.filter(user=request.user).order_by("-created_at")
    form = ComplaintForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        complaint = form.save(commit=False)
        complaint.user = request.user
        complaint.priority = ComplaintClassifier().explain_priority(
            complaint.description, complaint.category
        )["predicted_priority"]
        complaint.save()
        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=request.user,
            event_type="CREATED",
            new_value=complaint.status,
            note="Report submitted by resident.",
        )
        messages.success(request, f"Report {complaint.reference_number} was submitted.")
        return redirect("citizen-dashboard")

    counts = {
        "total": complaints.count(),
        "open": complaints.filter(status__in=["SUBMITTED", "UNDER_REVIEW", "IN_PROGRESS"]).count(),
        "resolved": complaints.filter(status="RESOLVED").count(),
    }
    recent_updates = complaints.exclude(status="SUBMITTED").order_by("-updated_at")[:4]
    return render(
        request,
        "citizen_dashboard.html",
        {
            "complaints": complaints[:20],
            "counts": counts,
            "recent_updates": recent_updates,
            "map_reports": list(
                complaints.exclude(latitude__isnull=True)
                .exclude(longitude__isnull=True)
                .values("id", "title", "category", "status", "latitude", "longitude")
            ),
            "form": form,
        },
    )


@login_required(login_url="/login/")
def complaint_detail(request, pk):
    complaint = get_object_or_404(
        Complaint.objects.select_related("user", "assigned_to").prefetch_related(
            "history__actor"
        ),
        pk=pk,
    )
    if not request.user.is_staff and complaint.user_id != request.user.id:
        messages.error(request, "You can only view your own reports.")
        return redirect("citizen-dashboard")

    prediction = ComplaintClassifier().predict(complaint.description)
    prediction["confidence_percent"] = round(prediction["confidence"] * 100)
    return render(
        request,
        "complaint_detail.html",
        {
            "complaint": complaint,
            "prediction": prediction,
            "feedback_form": ResolutionFeedbackForm(instance=complaint),
            "staff_users": User.objects.filter(is_staff=True).order_by("username"),
        },
    )


@login_required(login_url="/login/")
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "The operations dashboard is for authorized city staff.")
        return redirect("citizen-dashboard")

    all_complaints = Complaint.objects.select_related("user", "assigned_to").all()
    status_filter = request.GET.get("status", "all")
    category_filter = request.GET.get("category", "all")
    query = request.GET.get("q", "").strip()
    complaints = all_complaints.order_by("-created_at")

    valid_statuses = {choice[0] for choice in Complaint.STATUS_CHOICES}
    valid_categories = {choice[0] for choice in Complaint.CATEGORY_CHOICES}
    if status_filter not in valid_statuses:
        status_filter = "all"
    if category_filter not in valid_categories:
        category_filter = "all"
    if status_filter != "all":
        complaints = complaints.filter(status=status_filter)
    if category_filter != "all":
        complaints = complaints.filter(category=category_filter)
    if query:
        complaints = complaints.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    total = complaints.count()
    categories = Counter(complaints.values_list("category", flat=True))
    statuses = Counter(complaints.values_list("status", flat=True))
    resolution = complaints.filter(status="RESOLVED").aggregate(
        average=Avg(F("updated_at") - F("created_at"))
    )["average"]
    average_hours = round(resolution.total_seconds() / 3600, 1) if resolution else None
    category_labels = dict(Complaint.CATEGORY_CHOICES)
    status_labels = dict(Complaint.STATUS_CHOICES)

    map_reports = list(
        complaints.exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .values("id", "title", "category", "status", "latitude", "longitude")
    )
    department_labels = dict(Complaint.DEPARTMENT_CHOICES)
    departments = [
        {
            "key": key,
            "name": label,
            "count": complaints.filter(department=key).count(),
        }
        for key, label in Complaint.DEPARTMENT_CHOICES
    ]
    return render(
        request,
        "admin_dashboard.html",
        {
            "total_complaints": total,
            "pending_complaints": complaints.filter(status="SUBMITTED").count(),
            "resolved_complaints": complaints.filter(status="RESOLVED").count(),
            "in_progress_complaints": complaints.filter(status="IN_PROGRESS").count(),
            "high_priority_complaints": complaints.filter(
                priority__in=["HIGH", "CRITICAL"]
            ).count(),
            "sla_breached_complaints": breached_complaints(complaints).count(),
            "unassigned_complaints": complaints.filter(assigned_to__isnull=True).count(),
            "departments": departments,
            "categories": categories,
            "status_distribution": statuses,
            "category_chart": {
                "labels": [category_labels[key] for key in categories],
                "values": list(categories.values()),
            },
            "status_chart": {
                "labels": [status_labels[key] for key in statuses],
                "values": list(statuses.values()),
            },
            "average_resolution_hours": average_hours,
            "complaints": complaints[:30],
            "map_reports": map_reports,
            "status_filter": status_filter,
            "category_filter": category_filter,
            "query": query,
            "status_choices": Complaint.STATUS_CHOICES,
            "category_choices": Complaint.CATEGORY_CHOICES,
            "department_choices": Complaint.DEPARTMENT_CHOICES,
            "staff_users": User.objects.filter(is_staff=True).order_by("username"),
        },
    )


@login_required(login_url="/login/")
@require_POST
def update_complaint_status(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Only authorized city staff can update report status.")
        return redirect("citizen-dashboard")

    complaint = get_object_or_404(Complaint, pk=pk)
    next_status = request.POST.get("status")
    next_priority = request.POST.get("priority", complaint.priority)
    next_department = request.POST.get("department", complaint.department)
    next_assignee_id = request.POST.get(
        "assigned_to", str(complaint.assigned_to_id or "")
    )
    next_assignee = None
    if next_assignee_id:
        next_assignee = User.objects.filter(
            pk=next_assignee_id, is_staff=True
        ).first()

    if next_status not in {choice[0] for choice in Complaint.STATUS_CHOICES}:
        messages.error(request, "Choose a valid report status.")
    elif next_priority not in {choice[0] for choice in Complaint.PRIORITY_CHOICES}:
        messages.error(request, "Choose a valid report priority.")
    elif next_department not in {choice[0] for choice in Complaint.DEPARTMENT_CHOICES}:
        messages.error(request, "Choose a valid department.")
    elif next_assignee_id and next_assignee is None:
        messages.error(request, "Choose an active staff account for assignment.")
    else:
        changes = [
            ("STATUS", str(complaint.status), str(next_status)),
            ("PRIORITY", str(complaint.priority), str(next_priority)),
            ("ASSIGNMENT", str(complaint.department), str(next_department)),
            (
                "ASSIGNMENT",
                complaint.assigned_to.username if complaint.assigned_to else "",
                next_assignee.username if next_assignee else "",
            ),
        ]
        with transaction.atomic():
            complaint.status = next_status
            complaint.priority = next_priority
            complaint.department = next_department
            complaint.assigned_to = next_assignee
            complaint.save(
                update_fields=[
                    "status",
                    "priority",
                    "department",
                    "assigned_to",
                    "updated_at",
                ]
            )
            for event_type, old_value, new_value in changes:
                if old_value != new_value:
                    ComplaintHistory.objects.create(
                        complaint=complaint,
                        actor=request.user,
                        event_type=event_type,
                        old_value=old_value,
                        new_value=new_value,
                    )
        messages.success(request, f"{complaint.reference_number} status updated.")
    return redirect("admin-dashboard")


@login_required(login_url="/login/")
@require_POST
def submit_resolution_feedback(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, user=request.user)
    if request.user.is_staff or complaint.status != "RESOLVED":
        messages.error(
            request, "Feedback is available to the report owner after resolution."
        )
        return redirect("report-detail", pk=complaint.pk)

    form = ResolutionFeedbackForm(request.POST, instance=complaint)
    if form.is_valid():
        old_rating = complaint.resolution_rating
        with transaction.atomic():
            feedback = form.save()
            ComplaintHistory.objects.create(
                complaint=complaint,
                actor=request.user,
                event_type="FEEDBACK",
                old_value=str(old_rating or ""),
                new_value=str(feedback.resolution_rating or ""),
                note=feedback.resolution_feedback,
            )
        messages.success(request, "Thanks for sharing resolution feedback.")
    else:
        messages.error(request, "Choose a valid rating and try again.")
    return redirect("report-detail", pk=complaint.pk)


@login_required(login_url="/login/")
def knowledge_assistant(request):
    if not request.user.is_staff:
        messages.error(request, "The AI triage workspace is for authorized city staff.")
        return redirect("citizen-dashboard")

    result = None
    description = ""
    if request.method == "POST":
        description = request.POST.get("description", "").strip()
        if description:
            classifier = ComplaintClassifier()
            prediction = classifier.predict(description)
            similar = classifier.find_similar_complaints(
                description,
                list(
                    Complaint.objects.order_by("-created_at")
                    .values("id", "title", "description")[:15]
                ),
            )
            result = {
                "prediction": prediction,
                "priority": classifier.explain_priority(
                    description,
                    prediction["category"],
                    similar_reports=len(similar),
                ),
                "similar": similar,
            }
    return render(
        request,
        "ai_assistant.html",
        {"result": result, "description": description},
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_api(request):
    complaints = Complaint.objects.all()
    return Response(
        {
            "total_complaints": complaints.count(),
            "pending_complaints": complaints.filter(status="SUBMITTED").count(),
            "resolved_complaints": complaints.filter(status="RESOLVED").count(),
            "in_progress_complaints": complaints.filter(status="IN_PROGRESS").count(),
            "high_priority_complaints": complaints.filter(
                priority__in=["HIGH", "CRITICAL"]
            ).count(),
            "category_distribution": dict(
                Counter(complaints.values_list("category", flat=True))
            ),
            "status_distribution": dict(
                Counter(complaints.values_list("status", flat=True))
            ),
        }
    )
