from rest_framework import serializers

from .models import Complaint


class ComplaintSerializer(serializers.ModelSerializer):
    reference_number = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_id",
            "reference_number",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "latitude",
            "longitude",
            "image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "complaint_id",
            "reference_number",
            "priority",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {"latitude": "Latitude and longitude must be provided together."}
            )
        if latitude is not None and not -90 <= latitude <= 90:
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if longitude is not None and not -180 <= longitude <= 180:
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180."})
        return attrs

    def get_reference_number(self, obj):
        return obj.reference_number
