from django.urls import path

from .views import model_status, predict_category

urlpatterns = [
    path("predict/", predict_category, name="ai-predict"),
    path("status/", model_status, name="ai-status"),
]
