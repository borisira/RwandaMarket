from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminDashboardView,
    BookingViewSet,
    ComplaintViewSet,
    EnquiryViewSet,
    FavouriteViewSet,
    ListingViewSet,
    ListingPhotoView,
    NotificationViewSet,
    EmailVerifyView,
    PaymentViewSet,
    PropertyReportViewSet,
    QuoteViewSet,
    RegisterView,
    ReviewViewSet,
    SessionView,
    SupportTicketViewSet,
    SurveyorProfileViewSet,
    SurveyRequestViewSet,
    SurveyorDocumentView,
)

router = DefaultRouter()
router.register("listings", ListingViewSet, basename="listing")
router.register("favourites", FavouriteViewSet, basename="favourite")
router.register("enquiries", EnquiryViewSet, basename="enquiry")
router.register("surveyor-profiles", SurveyorProfileViewSet, basename="surveyor-profile")
router.register("survey-requests", SurveyRequestViewSet, basename="survey-request")
router.register("quotes", QuoteViewSet, basename="quote")
router.register("bookings", BookingViewSet, basename="booking")
router.register("reviews", ReviewViewSet, basename="review")
router.register("reports", PropertyReportViewSet, basename="report")
router.register("payments", PaymentViewSet, basename="payment")
router.register("complaints", ComplaintViewSet, basename="complaint")
router.register("support-tickets", SupportTicketViewSet, basename="support-ticket")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/email/verify/", EmailVerifyView.as_view(), name="email-verify"),
    path("auth/me/", SessionView.as_view(), name="session"),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("listings/<uuid:listing_id>/photos/", ListingPhotoView.as_view(), name="listing-photos"),
    path("listings/photos/<uuid:photo_id>/", ListingPhotoView.as_view(), name="listing-photo"),
    path("surveyor-documents/", SurveyorDocumentView.as_view(), name="surveyor-document-upload"),
    path("surveyor-documents/<uuid:document_id>/download/", SurveyorDocumentView.as_view(), name="surveyor-document-download"),
    path("", include(router.urls)),
]
