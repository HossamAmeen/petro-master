from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created", "user")  # Customize displayed fields
    ordering = ("-created",)  # Optional: Order by newest first
    list_per_page = 20  # Optional: Pagination

    # # Disable add, edit, and delete functionalities
    # def has_add_permission(self, request):
    #     return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    admin.site.site_header = "Notifications Management"
    admin.site.index_title = "Manage Notifications"
