import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", "Client / buyer"
        SELLER = "seller", "Seller / agent"
        SURVEYOR = "surveyor", "Surveyor"
        ADMIN = "admin", "Admin"

    class Language(models.TextChoices):
        RW = "rw", "Kinyarwanda"
        EN = "en", "English"
        FR = "fr", "Français"

    class AccountStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CLOSED = "closed", "Closed"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CLIENT)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.RW)
    status = models.CharField(max_length=16, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)
    is_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_admin(self):
        return self.is_staff or self.role == self.Role.ADMIN

    def __str__(self):
        return self.get_full_name() or self.username


class Listing(TimeStampedModel):
    class PropertyType(models.TextChoices):
        LAND = "land", "Land"
        HOUSE = "house", "House"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"
        SOLD = "sold", "Sold"
        CLOSED = "closed", "Closed"

    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="listings")
    title = models.CharField(max_length=180)
    description = models.TextField()
    property_type = models.CharField(max_length=12, choices=PropertyType.choices)
    price_rwf = models.DecimalField(max_digits=15, decimal_places=0)
    area_sqm = models.DecimalField(max_digits=12, decimal_places=2)
    province = models.CharField(max_length=80)
    district = models.CharField(max_length=80)
    sector = models.CharField(max_length=80, blank=True)
    cell = models.CharField(max_length=80, blank=True)
    village = models.CharField(max_length=80, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    upi = models.CharField(max_length=100, blank=True)
    photo_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    moderation_note = models.CharField(max_length=300, blank=True)
    views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class ListingPhoto(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="photos")
    image = models.FileField(upload_to="listing-photos/%Y/%m/")
    original_filename = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.original_filename} - {self.listing.title}"


class Favourite(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favourites")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="favourited_by")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "listing"], name="unique_user_favourite")]


class Enquiry(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="enquiries")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enquiries")
    message = models.TextField(max_length=2000)
    is_read = models.BooleanField(default=False)


class SurveyorProfile(TimeStampedModel):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="surveyor_profile")
    bio = models.TextField(blank=True)
    qualifications = models.CharField(max_length=250, blank=True)
    licence_number = models.CharField(max_length=100, blank=True)
    service_areas = models.CharField(max_length=250, blank=True)
    services = models.JSONField(default=list, blank=True)
    verification_status = models.CharField(
        max_length=12, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    rejection_reason = models.CharField(max_length=300, blank=True)
    years_experience = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"Surveyor: {self.user}"


class SurveyorDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        LICENCE = "licence", "Licence"
        QUALIFICATION = "qualification", "Qualification"
        IDENTITY = "identity", "Identity"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    surveyor = models.ForeignKey(SurveyorProfile, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="private/surveyor-documents/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.surveyor.user}"


class SurveyRequest(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        QUOTED = "quoted", "Quotes received"
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name="survey_requests")
    service = models.CharField(max_length=50)
    location = models.CharField(max_length=250)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    upi = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    desired_date = models.DateField(null=True, blank=True)
    budget_rwf = models.DecimalField(max_digits=15, decimal_places=0, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)

    def __str__(self):
        return f"{self.service} - {self.location}"


class Quote(TimeStampedModel):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CLOSED = "closed", "Closed"

    request = models.ForeignKey(SurveyRequest, on_delete=models.CASCADE, related_name="quotes")
    surveyor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="quotes")
    price_rwf = models.DecimalField(max_digits=15, decimal_places=0)
    timeline_days = models.PositiveSmallIntegerField()
    scope_notes = models.TextField(max_length=1500)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SENT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["request", "surveyor"], name="unique_quote_per_surveyor")]


class Booking(TimeStampedModel):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        IN_PROGRESS = "in_progress", "In progress"
        REPORT_SUBMITTED = "report_submitted", "Report submitted"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    request = models.OneToOneField(SurveyRequest, on_delete=models.PROTECT, related_name="booking")
    quote = models.OneToOneField(Quote, on_delete=models.PROTECT, related_name="booking")
    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name="bookings_as_client")
    surveyor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="bookings_as_surveyor")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BOOKED)
    report_file = models.FileField(upload_to="private/project-reports/", blank=True)
    report_text = models.TextField(blank=True)


class Review(TimeStampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="review")
    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(max_length=1200, blank=True)

    def __str__(self):
        return f"{self.rating}/5 - {self.booking_id}"


class PropertyReport(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        READY = "ready", "Ready"

    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="property_reports")
    listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.CharField(max_length=250)
    upi = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.READY)
    payment_status = models.CharField(max_length=12, default="not_configured")
    source_note = models.CharField(max_length=250, default="No authorised UPI or zoning data source configured")


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="payments")
    amount_rwf = models.DecimalField(max_digits=15, decimal_places=0)
    purpose = models.CharField(max_length=80)
    provider = models.CharField(max_length=80, default="not_configured")
    provider_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)


class Complaint(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWING = "reviewing", "Reviewing"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=180)
    details = models.TextField(max_length=3000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)


class SupportTicket(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=180)
    message = models.TextField(max_length=3000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)


class Notification(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=180)
    message = models.CharField(max_length=500)
    read_at = models.DateTimeField(null=True, blank=True)


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_entries")
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=80)
    details = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.action} {self.object_type} {self.object_id}"
