from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from complaints.models import Complaint
from .services import ComplaintClassifier

classifier = ComplaintClassifier()


@api_view(["POST"])
@permission_classes([AllowAny])
def predict_category(request):
    text = request.data.get("text") or request.data.get("description")
    if not text:
        return Response({"detail": "Text is required."}, status=status.HTTP_400_BAD_REQUEST)

    result = classifier.predict(text)
    similar = classifier.find_similar_complaints(
        text,
        list(Complaint.objects.order_by("-created_at").values("id", "title", "description")[:10]),
    )
    priority = classifier.explain_priority(text, result["category"], similar_reports=len(similar))
    return Response({"prediction": result, "similar_reports": similar, "priority": priority})


@api_view(["GET"])
@permission_classes([AllowAny])
def model_status(request):
    payload = classifier.load() or {"model": None, "metrics": {"accuracy": 0, "precision": 0, "recall": 0, "f1": 0}}
    return Response({"status": "ready", "metrics": payload.get("metrics", {})})
