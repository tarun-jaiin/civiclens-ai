from rest_framework import generics, permissions
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .models import Complaint, ComplaintHistory
from .serializers import ComplaintSerializer


class ComplaintListCreateView(generics.ListCreateAPIView):
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Complaint.objects.all().order_by("-created_at")
        return Complaint.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        complaint = serializer.save(user=self.request.user)
        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=self.request.user,
            event_type="CREATED",
            new_value=complaint.status,
            note="Report submitted through the API.",
        )


class ComplaintDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method in {"PUT", "PATCH", "DELETE"}:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.is_staff:
            return Complaint.objects.all()
        return Complaint.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        complaint = serializer.save()
        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=self.request.user,
            event_type="UPDATED",
            note="Report edited through the API.",
        )
