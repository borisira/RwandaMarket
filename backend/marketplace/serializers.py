from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import (
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
    SurveyorDocument,
    SupportTicket,
    SurveyRequest,
    SurveyorProfile,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "role", "language", "status", "is_verified", "is_staff",
        ]
        read_only_fields = ["id", "username", "status", "is_verified", "is_staff"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "language", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError("Admin accounts must be provisioned by an administrator.")
        return value

    def validate_password(self, value):
        requirements = (
            (len(value) >= 10, "Password must be at least 10 characters long."),
            (any(char.isupper() for char in value), "Password must include an uppercase letter."),
            (any(char.islower() for char in value), "Password must include a lowercase letter."),
            (any(char.isdigit() for char in value), "Password must include a number."),
            (any(not char.isalnum() for char in value), "Password must include a special character."),
        )
        errors = [message for valid, message in requirements if not valid]
        if errors:
            raise serializers.ValidationError(errors)
        validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data.pop("email")
        user = User.objects.create_user(username=email, email=email, **validated_data)
        if user.role == User.Role.SURVEYOR:
            SurveyorProfile.objects.create(user=user)
        return user


class ListingSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_role = serializers.CharField(source="owner.role", read_only=True)
    enquiry_count = serializers.IntegerField(read_only=True)
    photos = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "description", "property_type", "price_rwf", "area_sqm",
            "province", "district", "sector", "cell", "village",
            "latitude", "longitude", "upi", "photo_url", "photos",
            "status", "is_verified", "is_featured", "moderation_note", "views",
            "owner", "owner_name", "owner_role", "enquiry_count", "created_at",
        ]
        read_only_fields = [
            "id", "status", "is_verified", "is_featured", "moderation_note",
            "views", "owner", "owner_name", "owner_role", "enquiry_count", "created_at",
        ]

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username

    def get_photos(self, obj):
        request = self.context.get("request")
        if request is None:
            return []
        from django.core import signing
        from urllib.parse import urlencode

        return [
            request.build_absolute_uri(
                f"{reverse('listing-photo', kwargs={'photo_id': photo.pk}, request=request)}?"
                f"{urlencode({'access': signing.dumps(str(photo.pk), salt='marketplace.listing-photo')})}"
            )
            for photo in obj.photos.all()
        ]


class FavouriteSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    listing_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Favourite
        fields = ["id", "listing", "listing_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class EnquirySerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry
        fields = ["id", "listing", "sender", "sender_name", "message", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "sender_name", "is_read", "created_at"]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username


class SurveyorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    completed_jobs = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    verification_status = serializers.CharField(read_only=True)
    rejection_reason = serializers.CharField(read_only=True)

    class Meta:
        model = SurveyorProfile
        fields = [
            "id", "user", "full_name", "bio", "qualifications", "licence_number",
            "service_areas", "services", "verification_status", "rejection_reason",
            "years_experience", "rating", "completed_jobs", "documents",
        ]
        read_only_fields = ["id", "user", "full_name", "rating", "completed_jobs"]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_rating(self, obj):
        from django.db.models import Avg
        return obj.user.bookings_as_surveyor.filter(review__isnull=False).aggregate(avg=Avg("review__rating"))["avg"]

    def get_completed_jobs(self, obj):
        return obj.user.bookings_as_surveyor.filter(status=Booking.Status.COMPLETED).count()

    def get_documents(self, obj):
        request = self.context.get("request")
        if not request or (not getattr(request.user, "is_admin", False) and request.user != obj.user):
            return []
        return [
            {
                "id": str(document.pk),
                "document_type": document.get_document_type_display(),
                "original_filename": document.original_filename,
                "status": document.status,
                "created_at": document.created_at,
            }
            for document in obj.documents.order_by("-created_at")
        ]


class SurveyRequestSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    quote_count = serializers.IntegerField(read_only=True)
    quotes = serializers.SerializerMethodField()

    class Meta:
        model = SurveyRequest
        fields = [
            "id", "client", "client_name", "service", "location", "latitude", "longitude",
            "upi", "description", "desired_date", "budget_rwf", "status", "quote_count",
            "quotes", "created_at",
        ]
        read_only_fields = ["id", "client", "client_name", "status", "quote_count", "quotes", "created_at"]

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username

    def get_quotes(self, obj):
        queryset = obj.quotes.select_related("surveyor", "surveyor__surveyor_profile")
        request = self.context.get("request")
        if request and request.user != obj.client and not request.user.is_admin:
            queryset = queryset.filter(surveyor=request.user)
        return QuoteSerializer(queryset, many=True).data


class QuoteSerializer(serializers.ModelSerializer):
    surveyor_name = serializers.SerializerMethodField()
    surveyor_verified = serializers.SerializerMethodField()
    surveyor_rating = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            "id", "request", "surveyor", "surveyor_name", "surveyor_verified", "surveyor_rating",
            "price_rwf", "timeline_days", "scope_notes", "valid_until", "status", "created_at",
        ]
        read_only_fields = ["id", "surveyor", "surveyor_name", "surveyor_verified", "surveyor_rating", "status", "created_at"]

    def get_surveyor_name(self, obj):
        return obj.surveyor.get_full_name() or obj.surveyor.username

    def get_surveyor_verified(self, obj):
        return getattr(getattr(obj.surveyor, "surveyor_profile", None), "verification_status", "") == SurveyorProfile.VerificationStatus.VERIFIED

    def get_surveyor_rating(self, obj):
        from django.db.models import Avg
        return obj.surveyor.bookings_as_surveyor.filter(review__isnull=False).aggregate(avg=Avg("review__rating"))["avg"]


class BookingSerializer(serializers.ModelSerializer):
    request = SurveyRequestSerializer(read_only=True)
    quote = QuoteSerializer(read_only=True)
    client_name = serializers.SerializerMethodField()
    surveyor_name = serializers.SerializerMethodField()
    has_review = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id", "request", "quote", "client", "surveyor", "client_name",
            "surveyor_name", "status", "report_text", "has_review", "created_at",
        ]
        read_only_fields = fields

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username

    def get_surveyor_name(self, obj):
        return obj.surveyor.get_full_name() or obj.surveyor.username

    def get_has_review(self, obj):
        return hasattr(obj, "review")


class ReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    rating = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = ["id", "booking", "client", "client_name", "rating", "comment", "created_at"]
        read_only_fields = ["id", "client", "client_name", "created_at"]
        extra_kwargs = {"booking": {"write_only": True}}

    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username


class PropertyReportSerializer(serializers.ModelSerializer):
    listing_details = ListingSerializer(source="listing", read_only=True)
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = PropertyReport
        fields = [
            "id", "owner", "listing", "listing_details", "location", "upi", "status",
            "payment_status", "source_note", "disclaimer", "created_at",
        ]
        read_only_fields = [
            "id", "owner", "listing_details", "status", "payment_status", "source_note",
            "disclaimer", "created_at",
        ]
        extra_kwargs = {
            "location": {"required": False, "allow_blank": True},
            "upi": {"required": False, "allow_blank": True},
        }

    def get_disclaimer(self, obj):
        return "Decision aid only; not a government decision, title deed, ownership confirmation or building permit."


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount_rwf", "purpose", "provider", "provider_reference", "status", "created_at"]
        read_only_fields = ["id", "provider", "provider_reference", "status", "created_at"]


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ["id", "listing", "subject", "details", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class SupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SupportTicket
        fields = ["id", "user", "user_name", "user_email", "subject", "message", "status", "created_at"]
        read_only_fields = ["id", "user", "status", "created_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "read_at", "created_at"]
        read_only_fields = fields
