import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.core import signing
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db.models import Count, F, Q
from django.http import FileResponse, HttpResponse
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.views import APIView

from .models import (
    AuditLog,
    Booking,
    Complaint,
    Enquiry,
    Favourite,
    Listing,
    ListingPhoto,
    Notification,
    Payment,
    PropertyReport,
    Quote,
    Review,
    SupportTicket,
    SurveyRequest,
    SurveyorDocument,
    SurveyorProfile,
)
from .serializers import (
    BookingSerializer,
    ComplaintSerializer,
    EnquirySerializer,
    FavouriteSerializer,
    ListingSerializer,
    NotificationSerializer,
    PaymentSerializer,
    PropertyReportSerializer,
    QuoteSerializer,
    RegistrationSerializer,
    ReviewSerializer,
    SupportTicketSerializer,
    SurveyRequestSerializer,
    SurveyorProfileSerializer,
    UserSerializer,
)

User = get_user_model()


def audit(actor, action, obj, details=None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        details=details or {},
    )


def notify(user, title, message):
    Notification.objects.create(user=user, title=title, message=message)


def surveyor_matches(profile, survey_request):
    services = {service.strip().casefold() for service in profile.services if service.strip()}
    areas = [area.strip().casefold() for area in profile.service_areas.split(",") if area.strip()]
    location = survey_request.location.casefold()
    return survey_request.service.casefold() in services and any(area in location for area in areas)


class IsActiveAccount(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.status == User.AccountStatus.ACTIVE
        )


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return response.Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("username", "")
        password = request.data.get("password", "")
        if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password:
            raise ValidationError({"detail": "Enter your email address and password."})

        email = email.strip()
        user = User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).first()
        if user is None:
            raise ValidationError({"detail": "No account was found for that email address."})

        authenticated_user = authenticate(request, username=user.username, password=password)
        if authenticated_user is None:
            if not user.is_active:
                raise ValidationError({"detail": "This account is disabled. Contact support for help."})
            raise ValidationError({"detail": "The password is incorrect."})
        if user.status != User.AccountStatus.ACTIVE:
            raise ValidationError({"detail": "This account is not active. Contact support for help."})

        token, _ = Token.objects.get_or_create(user=authenticated_user)
        return response.Response({"token": token.key})


class SessionView(APIView):
    permission_classes = [IsActiveAccount]

    def get(self, request):
        return response.Response(UserSerializer(request.user).data)

    def delete(self, request):
        Token.objects.filter(user=request.user).delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request):
        allowed = {"first_name", "last_name", "language"}
        updates = allowed.intersection(request.data.keys())
        if "language" in updates and request.data["language"] not in User.Language.values:
            raise ValidationError({"language": "Choose Kinyarwanda, English or French."})
        for field in updates:
            setattr(request.user, field, request.data[field])
        request.user.save(update_fields=list(updates))
        return response.Response(UserSerializer(request.user).data)


class ListingViewSet(viewsets.ModelViewSet):
    serializer_class = ListingSerializer

    def get_queryset(self):
        queryset = Listing.objects.select_related("owner").prefetch_related("photos").annotate(enquiry_count=Count("enquiries"))
        user = self.request.user
        if user.is_staff:
            pass
        elif user.is_authenticated:
            queryset = queryset.filter(Q(status=Listing.Status.PUBLISHED) | Q(owner=user))
        else:
            queryset = queryset.filter(status=Listing.Status.PUBLISHED)
        params = self.request.query_params
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(province__icontains=search)
                | Q(district__icontains=search)
                | Q(sector__icontains=search)
                | Q(upi__iexact=search)
            )
        for param, field in (
            ("property_type", "property_type"),
            ("province", "province"),
            ("district", "district"),
        ):
            value = params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        if params.get("min_price"):
            queryset = queryset.filter(price_rwf__gte=params["min_price"])
        if params.get("max_price"):
            queryset = queryset.filter(price_rwf__lte=params["max_price"])
        if params.get("verified") == "true":
            queryset = queryset.filter(is_verified=True)
        return queryset.order_by("-is_featured", "-created_at")

    def get_permissions(self):
        if self.action in ("list", "retrieve", "view"):
            return [permissions.AllowAny()]
        return [IsActiveAccount()]

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.SELLER and not self.request.user.is_staff:
            raise PermissionDenied("Only seller accounts can create property listings.")
        listing = serializer.save(owner=self.request.user, status=Listing.Status.PENDING_REVIEW)
        audit(self.request.user, "listing.submitted", listing)

    def perform_update(self, serializer):
        listing = self.get_object()
        if not self.request.user.is_staff and listing.owner_id != self.request.user.id:
            raise PermissionDenied("You can only edit your own listings.")
        if self.request.user.is_staff:
            serializer.save()
        else:
            updated_listing = serializer.save(
                status=Listing.Status.PENDING_REVIEW,
                is_verified=False,
                moderation_note="",
            )
            audit(self.request.user, "listing.resubmitted", updated_listing)

    def destroy(self, request, *args, **kwargs):
        listing = self.get_object()
        if not request.user.is_staff and listing.owner_id != request.user.id:
            raise PermissionDenied("You can only close your own listings.")
        listing.status = Listing.Status.CLOSED
        listing.save(update_fields=["status", "updated_at"])
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=["post"])
    def view(self, request, pk=None):
        listing = self.get_object()
        Listing.objects.filter(pk=listing.pk).update(views=F("views") + 1)
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class ListingPhotoView(APIView):
    def get_permissions(self):
        return [permissions.AllowAny()] if self.request.method == "GET" else [IsActiveAccount()]

    def post(self, request, listing_id):
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            raise ValidationError({"listing": "This listing is not available."})
        if not request.user.is_staff and listing.owner_id != request.user.id:
            raise PermissionDenied("You can only add photos to your own listings.")

        uploads = request.FILES.getlist("files")
        if not uploads:
            raise ValidationError({"files": "Choose at least one photo to upload."})
        if listing.photos.count() + len(uploads) > 10:
            raise ValidationError({"files": "A listing can have up to 10 photos."})

        allowed = {
            ".jpg": ("image/jpeg", lambda header: header.startswith(b"\xff\xd8\xff")),
            ".jpeg": ("image/jpeg", lambda header: header.startswith(b"\xff\xd8\xff")),
            ".png": ("image/png", lambda header: header.startswith(b"\x89PNG\r\n\x1a\n")),
            ".webp": ("image/webp", lambda header: header[:4] == b"RIFF" and header[8:12] == b"WEBP"),
        }
        validated_uploads = []
        for upload in uploads:
            if upload.size > 5 * 1024 * 1024:
                raise ValidationError({"files": "Each photo must be 5 MB or smaller."})
            name = Path(upload.name.replace("\\", "/")).name
            extension = Path(name).suffix.lower()
            image_format = allowed.get(extension)
            if image_format is None or upload.content_type != image_format[0]:
                raise ValidationError({"files": "Upload photos in JPEG, PNG or WebP format."})
            header = upload.read(12)
            upload.seek(0)
            if not image_format[1](header):
                raise ValidationError({"files": "A selected file is not a valid image."})
            upload.name = f"{uuid.uuid4().hex}{extension}"
            validated_uploads.append((upload, name[:255]))

        for upload, name in validated_uploads:
            ListingPhoto.objects.create(listing=listing, image=upload, original_filename=name)
        listing.refresh_from_db()
        serialized = ListingSerializer(listing, context={"request": request}).data
        return response.Response({"photos": serialized["photos"]}, status=status.HTTP_201_CREATED)

    def get(self, request, photo_id):
        try:
            photo = ListingPhoto.objects.select_related("listing").get(pk=photo_id)
        except ListingPhoto.DoesNotExist:
            raise ValidationError("This photo is not available.")

        if photo.listing.status != Listing.Status.PUBLISHED:
            access = request.query_params.get("access", "")
            try:
                if signing.loads(
                    access,
                    salt="marketplace.listing-photo",
                    max_age=60 * 60,
                ) != str(photo.pk):
                    raise signing.BadSignature
            except signing.BadSignature:
                raise PermissionDenied("This photo is only available to the listing owner.")

        try:
            photo.image.open("rb")
        except (FileNotFoundError, OSError):
            raise ValidationError("The stored photo is unavailable.")
        return FileResponse(photo.image, filename=photo.original_filename)


class FavouriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavouriteSerializer
    permission_classes = [IsActiveAccount]

    def get_queryset(self):
        return Favourite.objects.filter(user=self.request.user).select_related("listing", "listing__owner")

    def create(self, request, *args, **kwargs):
        listing_id = request.data.get("listing_id")
        try:
            listing = Listing.objects.get(pk=listing_id, status=Listing.Status.PUBLISHED)
        except (Listing.DoesNotExist, ValueError):
            raise ValidationError({"listing_id": "Choose a published listing."})
        favourite, _ = Favourite.objects.get_or_create(user=request.user, listing=listing)
        return response.Response(FavouriteSerializer(favourite).data, status=status.HTTP_201_CREATED)


class EnquiryViewSet(viewsets.ModelViewSet):
    serializer_class = EnquirySerializer
    permission_classes = [IsActiveAccount]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = Enquiry.objects.select_related("sender", "listing")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(Q(sender=self.request.user) | Q(listing__owner=self.request.user))

    def perform_create(self, serializer):
        listing = serializer.validated_data["listing"]
        if listing.status != Listing.Status.PUBLISHED:
            raise ValidationError({"listing": "Enquiries are only available for published listings."})
        if listing.owner_id == self.request.user.id:
            raise ValidationError({"listing": "You cannot enquire about your own listing."})
        enquiry = serializer.save(sender=self.request.user)
        notify(listing.owner, "New property enquiry", f"A buyer asked about {listing.title}.")


class SurveyorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = SurveyorProfileSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        return [IsActiveAccount()]

    def get_queryset(self):
        queryset = SurveyorProfile.objects.select_related("user")
        if self.action == "list":
            queryset = queryset.filter(verification_status=SurveyorProfile.VerificationStatus.VERIFIED)
        elif not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(verification_status=SurveyorProfile.VerificationStatus.VERIFIED)
                | Q(user=self.request.user)
            )
        if self.request.query_params.get("service"):
            queryset = queryset.filter(services__icontains=self.request.query_params["service"])
        if self.request.query_params.get("area"):
            queryset = queryset.filter(service_areas__icontains=self.request.query_params["area"])
        return queryset

    def perform_update(self, serializer):
        profile = self.get_object()
        if not self.request.user.is_staff and profile.user_id != self.request.user.id:
            raise PermissionDenied("You can only edit your own surveyor profile.")
        self._save_profile(serializer, profile)

    def _save_profile(self, serializer, profile):
        verified_fields = {"qualifications", "licence_number", "service_areas", "services"}
        changed_verification_data = verified_fields.intersection(self.request.data.keys())
        if profile.verification_status == SurveyorProfile.VerificationStatus.VERIFIED and changed_verification_data:
            profile = serializer.save(
                verification_status=SurveyorProfile.VerificationStatus.PENDING,
                rejection_reason="",
            )
            notify(profile.user, "Surveyor profile review required", "Your verification details changed and must be reviewed again.")
            audit(self.request.user, "surveyor.profile_reverification_required", profile)
        else:
            serializer.save()

    @decorators.action(detail=False, methods=["get", "patch"])
    def me(self, request):
        if request.user.role != User.Role.SURVEYOR:
            raise PermissionDenied("This account is not a surveyor account.")
        profile, _ = SurveyorProfile.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self._save_profile(serializer, profile)
            return response.Response(serializer.data)
        return response.Response(self.get_serializer(profile).data)


class SurveyRequestViewSet(viewsets.ModelViewSet):
    serializer_class = SurveyRequestSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = SurveyRequest.objects.select_related("client").annotate(quote_count=Count("quotes"))
        if user.is_staff:
            return queryset.order_by("-created_at")
        if user.role == User.Role.SURVEYOR:
            profile = getattr(user, "surveyor_profile", None)
            if not profile or profile.verification_status != SurveyorProfile.VerificationStatus.VERIFIED:
                return queryset.none()
            service_filter = Q()
            for service in profile.services:
                service_filter |= Q(service__iexact=service.strip())
            area_filter = Q()
            for area in profile.service_areas.split(","):
                if area.strip():
                    area_filter |= Q(location__icontains=area.strip())
            if not profile.services or not area_filter:
                return queryset.none()
            return queryset.filter(
                service_filter,
                area_filter,
                status__in=[SurveyRequest.Status.OPEN, SurveyRequest.Status.QUOTED],
            ).exclude(client=user).order_by("-created_at")
        return queryset.filter(client=user).order_by("-created_at")

    def get_permissions(self):
        return [IsActiveAccount()]

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.CLIENT:
            raise PermissionDenied("Only client accounts can request a survey.")
        serializer.save(client=self.request.user)


class QuoteViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    permission_classes = [IsActiveAccount]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = Quote.objects.select_related("surveyor", "request", "surveyor__surveyor_profile")
        if user.is_staff:
            return queryset
        return queryset.filter(Q(surveyor=user) | Q(request__client=user))

    def perform_create(self, serializer):
        user = self.request.user
        profile = getattr(user, "surveyor_profile", None)
        if user.role != User.Role.SURVEYOR or not profile or profile.verification_status != SurveyorProfile.VerificationStatus.VERIFIED:
            raise PermissionDenied("Only verified surveyors can submit quotes.")
        survey_request = serializer.validated_data["request"]
        if not surveyor_matches(profile, survey_request):
            raise PermissionDenied("This request does not match your listed services and service areas.")
        if survey_request.status not in (SurveyRequest.Status.OPEN, SurveyRequest.Status.QUOTED):
            raise ValidationError({"request": "This request is no longer accepting quotes."})
        quote = serializer.save(surveyor=user)
        survey_request.status = SurveyRequest.Status.QUOTED
        survey_request.save(update_fields=["status", "updated_at"])
        notify(survey_request.client, "New survey quote", f"A surveyor sent a quote for {survey_request.service}.")
        audit(user, "quote.submitted", quote)

    @decorators.action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        user = request.user
        with transaction.atomic():
            quote = Quote.objects.select_for_update().select_related("request").get(pk=pk)
            if quote.request.client_id != user.id:
                raise PermissionDenied("Only the client who created this request can accept a quote.")
            if quote.status != Quote.Status.SENT:
                raise ValidationError("This quote is no longer available.")
            if Booking.objects.filter(request=quote.request).exists():
                raise ValidationError("A surveyor has already been booked for this request.")
            quote.status = Quote.Status.ACCEPTED
            quote.save(update_fields=["status", "updated_at"])
            Quote.objects.filter(request=quote.request).exclude(pk=quote.pk).update(status=Quote.Status.CLOSED)
            booking = Booking.objects.create(
                request=quote.request,
                quote=quote,
                client=user,
                surveyor=quote.surveyor,
            )
            quote.request.status = SurveyRequest.Status.BOOKED
            quote.request.save(update_fields=["status", "updated_at"])
            notify(quote.surveyor, "Quote accepted", "Your survey quote was accepted.")
            audit(user, "quote.accepted", quote, {"booking_id": str(booking.pk)})
        return response.Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsActiveAccount]

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.select_related("request", "quote", "client", "surveyor")
        if user.is_staff:
            return queryset
        return queryset.filter(Q(client=user) | Q(surveyor=user))

    @decorators.action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        booking = self.get_object()
        next_status = request.data.get("status")
        allowed = {
            Booking.Status.BOOKED: {Booking.Status.IN_PROGRESS, Booking.Status.CANCELLED},
            Booking.Status.IN_PROGRESS: {Booking.Status.REPORT_SUBMITTED, Booking.Status.CANCELLED},
            Booking.Status.REPORT_SUBMITTED: {Booking.Status.COMPLETED},
        }
        if next_status not in allowed.get(booking.status, set()):
            raise ValidationError({"status": "This project status transition is not allowed."})
        if next_status in (Booking.Status.IN_PROGRESS, Booking.Status.REPORT_SUBMITTED) and booking.surveyor_id != request.user.id and not request.user.is_staff:
            raise PermissionDenied("Only the assigned surveyor can update this project.")
        if next_status == Booking.Status.COMPLETED and booking.client_id != request.user.id and not request.user.is_staff:
            raise PermissionDenied("Only the client can confirm project completion.")
        if next_status == Booking.Status.REPORT_SUBMITTED:
            report_text = request.data.get("report_text", "").strip()
            if len(report_text) < 20:
                raise ValidationError({"report_text": "Please include at least 20 characters in the project report."})
            booking.report_text = report_text
        booking.status = next_status
        booking.save(update_fields=["status", "report_text", "updated_at"])
        if next_status == Booking.Status.COMPLETED:
            booking.request.status = SurveyRequest.Status.COMPLETED
            booking.request.save(update_fields=["status", "updated_at"])
        notify(
            booking.client if request.user == booking.surveyor else booking.surveyor,
            "Project update",
            f"The survey project is now {booking.get_status_display().lower()}.",
        )
        audit(request.user, "booking.status_changed", booking, {"status": next_status})
        return response.Response(self.get_serializer(booking).data)

    @decorators.action(detail=True, methods=["get"])
    def download_report(self, request, pk=None):
        booking = self.get_object()
        if not booking.report_text:
            raise ValidationError("The surveyor has not submitted a report yet.")
        return HttpResponse(
            booking.report_text,
            content_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="survey-report-{booking.pk}.txt"'},
        )


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        return [IsActiveAccount()]

    def get_queryset(self):
        queryset = Review.objects.select_related("client", "booking", "booking__surveyor")
        surveyor_id = self.request.query_params.get("surveyor")
        if surveyor_id:
            queryset = queryset.filter(booking__surveyor_id=surveyor_id)
        return queryset

    def perform_create(self, serializer):
        booking = serializer.validated_data["booking"]
        if booking.client_id != self.request.user.id:
            raise PermissionDenied("Only the client who booked the survey can leave a review.")
        if booking.status != Booking.Status.COMPLETED:
            raise ValidationError({"booking": "Reviews are available after a booking is completed."})
        if hasattr(booking, "review"):
            raise ValidationError({"booking": "You have already reviewed this completed booking."})
        serializer.save(client=self.request.user)


class PropertyReportViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyReportSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [IsActiveAccount]

    def get_queryset(self):
        queryset = PropertyReport.objects.select_related("listing")
        return queryset if self.request.user.is_staff else queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        listing = serializer.validated_data.get("listing")
        if listing and listing.status != Listing.Status.PUBLISHED:
            raise ValidationError({"listing": "A report can only be ordered for a published listing."})
        serializer.save(
            owner=self.request.user,
            location=serializer.validated_data.get("location") or (listing.district if listing else ""),
            upi=serializer.validated_data.get("upi") or (listing.upi if listing else ""),
        )

    @decorators.action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        report = self.get_object()
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle(f"Property Insight Report {report.pk}")
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(48, 746, "O.M.N RwandaMarket")
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(48, 712, "Property Insight Report (preview)")
        pdf.setFont("Helvetica", 10)
        lines = [
            f"Report reference: {report.pk}",
            f"Created: {report.created_at:%Y-%m-%d %H:%M} UTC",
            f"Location: {report.location or 'Not provided'}",
            f"UPI: {report.upi or 'No authorised parcel data found'}",
            f"Property: {report.listing.title if report.listing else 'User-supplied location'}",
            f"Listing data status: {'Seller submitted; not independently verified' if report.listing else 'User supplied; unverified'}",
            "",
            "Official parcel and Master Plan sources are not connected in this preview.",
            "No ownership, boundary or zoning information has been inferred.",
            "",
            "Sources and data dates",
            report.source_note,
            "",
            "Unverified information",
            "Property details and location data in this preview have not been independently confirmed.",
            "",
            "IMPORTANT DISCLAIMER",
            "This report is a decision aid only. It is not a government decision, title deed,",
            "proof of ownership, legal boundary survey or building permit.",
            "Master Plan information, when available, is not a building permit.",
            "",
            "Payments are not available until an approved provider is configured.",
        ]
        y = 680
        for line in lines:
            if y < 55:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = 746
            pdf.drawString(48, y, line[:110])
            y -= 18
        pdf.save()
        buffer.seek(0)
        return HttpResponse(
            buffer.getvalue(),
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="property-report-{report.pk}.pdf"'},
        )


class SurveyorDocumentView(APIView):
    permission_classes = [IsActiveAccount]

    def post(self, request):
        if request.user.role != User.Role.SURVEYOR:
            raise PermissionDenied("Only surveyors can upload verification documents.")
        upload = request.FILES.get("file")
        document_type = request.data.get("document_type")
        if document_type not in SurveyorDocument.DocumentType.values:
            raise ValidationError({"document_type": "Choose a valid document type."})
        if upload is None:
            raise ValidationError({"file": "Select a document to upload."})
        if upload.size > 5 * 1024 * 1024:
            raise ValidationError({"file": "Documents must be 5 MB or smaller."})
        allowed = {
            ".pdf": (b"%PDF-", "application/pdf"),
            ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
            ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
            ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
        }
        name = upload.name.replace("\r", "").replace("\n", "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        expected = allowed.get(extension)
        if not expected or upload.content_type != expected[1] or upload.read(len(expected[0])) != expected[0]:
            raise ValidationError({"file": "Upload a valid PDF, JPEG or PNG document."})
        upload.seek(0)
        profile, _ = SurveyorProfile.objects.get_or_create(user=request.user)
        document = SurveyorDocument.objects.create(
            surveyor=profile,
            document_type=document_type,
            file=upload,
            original_filename=name[:255],
        )
        if profile.verification_status == SurveyorProfile.VerificationStatus.VERIFIED:
            profile.verification_status = SurveyorProfile.VerificationStatus.PENDING
            profile.rejection_reason = ""
            profile.save(update_fields=["verification_status", "rejection_reason", "updated_at"])
            notify(request.user, "Surveyor profile review required", "Your profile must be reviewed after a new verification document is uploaded.")
        audit(request.user, "surveyor.document_uploaded", document, {"document_type": document_type})
        return response.Response(
            {"id": str(document.pk), "document_type": document.get_document_type_display(), "status": document.status},
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, document_id):
        try:
            document = SurveyorDocument.objects.select_related("surveyor", "surveyor__user").get(pk=document_id)
        except (SurveyorDocument.DoesNotExist, DjangoValidationError):
            raise ValidationError("This document is not available.")
        if not request.user.is_staff and document.surveyor.user_id != request.user.id:
            raise PermissionDenied("You do not have access to this document.")
        try:
            document.file.open("rb")
        except (FileNotFoundError, OSError):
            raise ValidationError("The stored document is unavailable.")
        return FileResponse(
            document.file,
            as_attachment=True,
            filename=document.original_filename,
        )


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [IsActiveAccount]

    def get_queryset(self):
        queryset = Payment.objects.all()
        return queryset if self.request.user.is_staff else queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        raise ValidationError({
            "payment": "Payments are not enabled. Configure and verify an approved payment provider before charging users."
        })


class ComplaintViewSet(viewsets.ModelViewSet):
    serializer_class = ComplaintSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [IsActiveAccount]

    def get_queryset(self):
        queryset = Complaint.objects.select_related("reporter", "listing")
        return queryset if self.request.user.is_staff else queryset.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [IsActiveAccount]

    def get_queryset(self):
        queryset = SupportTicket.objects.select_related("user")
        return queryset if self.request.user.is_staff else queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsActiveAccount]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")


class AdminDashboardView(APIView):
    permission_classes = [IsActiveAccount]

    def get(self, request):
        if not request.user.is_staff:
            raise PermissionDenied("Administrator access is required.")
        return response.Response({
            "users": User.objects.count(),
            "surveyors_pending": SurveyorProfile.objects.filter(verification_status=SurveyorProfile.VerificationStatus.PENDING).count(),
            "listings_pending": Listing.objects.filter(status=Listing.Status.PENDING_REVIEW).count(),
            "open_complaints": Complaint.objects.filter(status=Complaint.Status.OPEN).count(),
            "open_support_tickets": SupportTicket.objects.filter(status=SupportTicket.Status.OPEN).count(),
            "audit_logs": list(AuditLog.objects.select_related("actor").order_by("-created_at")[:30].values(
                "id", "action", "object_type", "object_id", "created_at", "actor__username"
            )),
            "surveyors": SurveyorProfileSerializer(
                SurveyorProfile.objects.select_related("user").order_by("verification_status", "-created_at")[:100],
                many=True,
                context={"request": request},
            ).data,
            "listings": ListingSerializer(
                Listing.objects.select_related("owner").annotate(enquiry_count=Count("enquiries"))
                .exclude(status=Listing.Status.PUBLISHED).order_by("-created_at")[:100],
                many=True,
            ).data,
        })

    def patch(self, request):
        if not request.user.is_staff:
            raise PermissionDenied("Administrator access is required.")
        object_type = request.data.get("type")
        object_id = request.data.get("id")
        decision = request.data.get("decision")
        reason = request.data.get("reason", "").strip()
        if object_type == "listing":
            listing = Listing.objects.get(pk=object_id)
            if decision not in ("approve", "reject", "suspend"):
                raise ValidationError({"decision": "Choose approve, reject or suspend."})
            listing.status = {
                "approve": Listing.Status.PUBLISHED,
                "reject": Listing.Status.REJECTED,
                "suspend": Listing.Status.SUSPENDED,
            }[decision]
            listing.is_verified = decision == "approve"
            listing.moderation_note = reason
            listing.save(update_fields=["status", "is_verified", "moderation_note", "updated_at"])
            audit(request.user, f"listing.{decision}d", listing, {"reason": reason})
            notify(listing.owner, "Listing review complete", f"Your listing “{listing.title}” is {listing.get_status_display().lower()}.")
            return response.Response(ListingSerializer(listing).data)
        if object_type == "surveyor":
            profile = SurveyorProfile.objects.select_related("user").get(pk=object_id)
            if decision not in ("approve", "reject"):
                raise ValidationError({"decision": "Choose approve or reject."})
            if decision == "reject" and not reason:
                raise ValidationError({"reason": "A rejection reason is required."})
            reviewable_documents = profile.documents.filter(
                status__in=[SurveyorDocument.Status.PENDING, SurveyorDocument.Status.APPROVED]
            )
            if decision == "approve" and not reviewable_documents.exists():
                raise ValidationError({"documents": "Upload and review at least one verification document before approving this surveyor."})
            profile.verification_status = (
                SurveyorProfile.VerificationStatus.VERIFIED if decision == "approve"
                else SurveyorProfile.VerificationStatus.REJECTED
            )
            profile.rejection_reason = "" if decision == "approve" else reason
            profile.save(update_fields=["verification_status", "rejection_reason", "updated_at"])
            profile.documents.filter(status=SurveyorDocument.Status.PENDING).update(
                status=SurveyorDocument.Status.APPROVED if decision == "approve" else SurveyorDocument.Status.REJECTED
            )
            audit(request.user, f"surveyor.{decision}d", profile, {"reason": reason})
            notify(profile.user, "Surveyor verification updated", f"Your profile was {profile.verification_status}.")
            return response.Response(SurveyorProfileSerializer(profile).data)
        raise ValidationError({"type": "Choose listing or surveyor."})
