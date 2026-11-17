from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    AuditLog,
    Booking,
    Complaint,
    Enquiry,
    Favourite,
    Listing,
    Notification,
    Payment,
    PropertyReport,
    Quote,
    Review,
    SupportTicket,
    SurveyRequest,
    SurveyorProfile,
    User,
)


@admin.register(User)
class MarketplaceUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("RwandaMarket", {"fields": ("role", "language", "status", "is_verified")}),)
    list_display = ("username", "email", "role", "status", "is_verified", "is_staff")
    list_filter = ("role", "status", "is_verified", "is_staff")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "property_type", "district", "price_rwf", "status", "is_verified", "created_at")
    list_filter = ("status", "property_type", "is_verified", "province")
    search_fields = ("title", "description", "upi", "district", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at", "views")


@admin.register(SurveyorProfile)
class SurveyorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "verification_status", "service_areas", "years_experience", "updated_at")
    list_filter = ("verification_status",)
    search_fields = ("user__email", "user__first_name", "user__last_name", "licence_number")
    readonly_fields = ("id", "created_at", "updated_at")


class ReadOnlyAuditAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "object_type")
    search_fields = ("actor__username", "object_id")
    readonly_fields = ("id", "created_at", "updated_at", "actor", "action", "object_type", "object_id", "details")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(AuditLog, ReadOnlyAuditAdmin)
admin.site.register([SurveyRequest, Quote, Booking, Review, PropertyReport, Complaint, SupportTicket, Enquiry, Favourite, Notification])


@admin.register(Payment)
class ReadOnlyPaymentAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "purpose", "amount_rwf", "provider", "status")
    list_filter = ("status", "provider")
    search_fields = ("user__username", "provider_reference", "purpose")
    readonly_fields = ("id", "created_at", "updated_at", "user", "amount_rwf", "purpose", "provider", "provider_reference", "status")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
