
from django.contrib import admin
from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'user',
        'category',
        'priority',
        'status',
        'created_at',
    )

    list_filter = (
        'category',
        'priority',
        'status',
    )

    search_fields = (
        'title',
        'description',
        'user__username',
    )

    readonly_fields = (
        'complaint_id',
        'created_at',
        'updated_at',
    )

    ordering = ('-created_at',)
