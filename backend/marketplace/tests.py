import os
import tempfile
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Booking, Listing, Quote, SupportTicket, SurveyRequest, SurveyorProfile

User = get_user_model()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MarketplaceApiTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client@example.com",
            email="client@example.com",
            password="SecurePassword123!",
            role=User.Role.CLIENT,
        )
        self.seller = User.objects.create_user(
            username="seller@example.com",
            email="seller@example.com",
            password="SecurePassword123!",
            role=User.Role.SELLER,
        )
        self.other_seller = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="SecurePassword123!",
            role=User.Role.SELLER,
        )
        self.surveyor = User.objects.create_user(
            username="surveyor@example.com",
            email="surveyor@example.com",
            password="SecurePassword123!",
            role=User.Role.SURVEYOR,
        )
        self.surveyor_profile = SurveyorProfile.objects.create(
            user=self.surveyor,
            verification_status=SurveyorProfile.VerificationStatus.VERIFIED,
            services=["Boundary survey"],
            service_areas="Gasabo",
        )
        self.listing = Listing.objects.create(
            owner=self.seller,
            title="Published test plot",
            description="A test property.",
            property_type=Listing.PropertyType.LAND,
            price_rwf=1000000,
            area_sqm=300,
            province="Kigali City",
            district="Gasabo",
            latitude=-1.9,
            longitude=30.1,
            status=Listing.Status.PUBLISHED,
        )
        self.private_listing = Listing.objects.create(
            owner=self.other_seller,
            title="Private listing",
            description="Awaiting review.",
            property_type=Listing.PropertyType.LAND,
            price_rwf=900000,
            area_sqm=250,
            province="Kigali City",
            district="Gasabo",
            latitude=-1.9,
            longitude=30.1,
            status=Listing.Status.PENDING_REVIEW,
        )
        self.request_obj = SurveyRequest.objects.create(
            client=self.client_user,
            service="Boundary survey",
            location="Gasabo",
            description="Confirm the boundaries of my parcel.",
        )

        self.quote = Quote.objects.create(
            request=self.request_obj,
            surveyor=self.surveyor,
            price_rwf=250000,
            timeline_days=5,
            scope_notes="Boundary measurements and a written summary.",
        )
        self.other_surveyor = User.objects.create_user(
            username="surveyor2@example.com",
            email="surveyor2@example.com",
            password="SecurePassword123!",
            role=User.Role.SURVEYOR,
        )
        SurveyorProfile.objects.create(
            user=self.other_surveyor,
            verification_status=SurveyorProfile.VerificationStatus.VERIFIED,
        )
        self.second_quote = Quote.objects.create(
            request=self.request_obj,
            surveyor=self.other_surveyor,
            price_rwf=275000,
            timeline_days=7,
            scope_notes="Boundary survey and field notes.",
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        EMAIL_HOST_USER="mailer@example.com",
        EMAIL_HOST_PASSWORD="smtp-test-password",
        DEFAULT_FROM_EMAIL="mailer@example.com",
    )
    def test_verification_email_is_sent_from_configured_sender(self):
        from .email_verification import send_verification_email

        send_verification_email(
            self.client_user,
            "https://api.example.com/api/auth/email/verify/?token=signed-token",
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "mailer@example.com")
        self.assertEqual(mail.outbox[0].to, [self.client_user.email])
        self.assertIn("LandLink", mail.outbox[0].subject)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        html_body, content_type = mail.outbox[0].alternatives[0]
        self.assertEqual(content_type, "text/html")
        self.assertIn("Verify my email", html_body)
        self.assertIn("signed-token", html_body)
        self.assertIn("LandLink", html_body)

    def test_login_explains_unknown_email_and_incorrect_password(self):
        self.client_user.set_password("CorrectPassword123!")
        self.client_user.save(update_fields=["password"])

        missing_account = self.client.post(
            reverse("api-token-auth"),
            {"username": "missing@example.com", "password": "any-password"},
            format="json",
        )
        self.assertEqual(missing_account.status_code, 400)
        self.assertEqual(
            missing_account.data["detail"],
            "No account was found for that email address.",
        )

        wrong_password = self.client.post(
            reverse("api-token-auth"),
            {"username": self.client_user.email, "password": "incorrect-password"},
            format="json",
        )
        self.assertEqual(wrong_password.status_code, 400)
        self.assertEqual(wrong_password.data["detail"], "The password is incorrect.")

        successful_login = self.client.post(
            reverse("api-token-auth"),
            {"username": self.client_user.email, "password": "CorrectPassword123!"},
            format="json",
        )
        self.assertEqual(successful_login.status_code, 200)
        self.assertIn("token", successful_login.data)

    def test_listing_photos_can_be_uploaded_and_private_photos_need_signed_urls(self):
        self.authenticate(self.seller)
        self.listing.status = Listing.Status.PENDING_REVIEW
        self.listing.save(update_fields=["status"])
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            image = SimpleUploadedFile(
                "front.jpg",
                b"\xff\xd8\xff" + b"listing photo",
                content_type="image/jpeg",
            )
            uploaded = self.client.post(
                reverse("listing-photos", args=[self.listing.pk]),
                {"files": [image]},
                format="multipart",
            )
            self.assertEqual(uploaded.status_code, 201)
            self.assertEqual(len(uploaded.data["photos"]), 1)

            photo_url = urlsplit(uploaded.data["photos"][0])
            self.client.credentials()
            private_photo = self.client.get(photo_url.path)
            self.assertEqual(private_photo.status_code, 403)
            private_photo.close()
            signed_photo = self.client.get(f"{photo_url.path}?{photo_url.query}")
            self.assertEqual(signed_photo.status_code, 200)
            signed_photo.close()

            self.listing.status = Listing.Status.PUBLISHED
            self.listing.save(update_fields=["status"])
            public_photo = self.client.get(photo_url.path)
            self.assertEqual(public_photo.status_code, 200)
            public_photo.close()

    def test_registration_password_requirements_are_returned_immediately(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "new-user@example.com",
                "first_name": "New",
                "last_name": "User",
                "role": User.Role.CLIENT,
                "language": User.Language.EN,
                "password": "short",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        password_errors = response.data["password"]
        self.assertIn("Password must be at least 10 characters long.", password_errors)
        self.assertIn("Password must include an uppercase letter.", password_errors)
        self.assertIn("Password must include a number.", password_errors)
        self.assertIn("Password must include a special character.", password_errors)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        EMAIL_HOST_USER="mailer@example.com",
        EMAIL_HOST_PASSWORD="smtp-test-password",
        DEFAULT_FROM_EMAIL="mailer@example.com",
        FRONTEND_URL="https://landlink.example",
    )
    def test_registration_sends_email_immediately_and_link_activates_account(self):
        registration = self.client.post(
            reverse("register"),
            {
                "email": "email-only@example.com",
                "first_name": "Email",
                "last_name": "Only",
                "role": User.Role.CLIENT,
                "language": User.Language.EN,
                "password": "Qm7!vZ4@pL9#tR2",
            },
            format="json",
        )

        self.assertEqual(registration.status_code, 202)
        self.assertTrue(registration.data["verification_required"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["email-only@example.com"])
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        user = User.objects.get(email="email-only@example.com")
        self.assertEqual(user.status, User.AccountStatus.PENDING)
        verification_url = next(
            line for line in mail.outbox[0].body.splitlines() if line.startswith("http")
        )
        token = parse_qs(urlsplit(verification_url).query)["token"][0]

        verified = self.client.get(reverse("email-verify"), {"token": token})

        self.assertEqual(verified.status_code, 302)
        self.assertEqual(verified["Location"], "https://landlink.example/?email_verified=1")
        user.refresh_from_db()
        self.assertEqual(user.status, User.AccountStatus.ACTIVE)
        self.assertTrue(user.is_verified)
        self.assertIsNotNone(user.email_verified_at)

        login = self.client.post(
            reverse("api-token-auth"),
            {"username": user.email, "password": "Qm7!vZ4@pL9#tR2"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("token", login.data)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="smtp.example.com",
        EMAIL_HOST_USER="mailer@example.com",
        EMAIL_HOST_PASSWORD="smtp-test-password",
        DEFAULT_FROM_EMAIL="mailer@example.com",
    )
    def test_registration_needs_only_email_and_smtp_configuration(self):
        registration = self.client.post(
            reverse("register"),
            {
                "email": "email-only-config@example.com",
                "first_name": "Email",
                "last_name": "Only",
                "password": "Qm7!vZ4@pL9#tR2",
            },
            format="json",
        )

        self.assertEqual(registration.status_code, 202)
        self.assertTrue(User.objects.filter(email="email-only-config@example.com").exists())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST="",
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
        DEFAULT_FROM_EMAIL="",
    )
    def test_registration_fails_closed_when_smtp_is_unconfigured(self):
        email = "email-config-missing@example.com"
        registration = self.client.post(
            reverse("register"),
            {
                "email": email,
                "first_name": "Email",
                "last_name": "Only",
                "password": "Qm7!vZ4@pL9#tR2",
            },
            format="json",
        )

        self.assertEqual(registration.status_code, 503)
        self.assertFalse(User.objects.filter(email=email).exists())

    @override_settings(
        EMAIL_HOST="smtp.example.com",
        EMAIL_HOST_USER="mailer@example.com",
        EMAIL_HOST_PASSWORD="smtp-test-password",
        DEFAULT_FROM_EMAIL="mailer@example.com",
    )
    @patch("marketplace.views.send_verification_email")
    def test_email_delivery_failure_does_not_leave_pending_account(self, send_email):
        from .email_verification import EmailDeliveryError

        send_email.side_effect = EmailDeliveryError("SMTP unavailable")
        failed = self.client.post(
            reverse("register"),
            {
                "email": "email-failed@example.com",
                "first_name": "Email",
                "last_name": "Failed",
                "password": "Qm7!vZ4@pL9#tR2",
            },
            format="json",
        )

        self.assertEqual(failed.status_code, 503)
        self.assertFalse(User.objects.filter(email="email-failed@example.com").exists())

    @override_settings(FRONTEND_URL="https://landlink.example")
    def test_invalid_email_verification_link_does_not_activate_account(self):
        invalid = self.client.get(reverse("email-verify"), {"token": "invalid"})

        self.assertEqual(invalid.status_code, 302)
        self.assertEqual(invalid["Location"], "https://landlink.example/?email_verified=0")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="support-test@landlink.example",
    )
    def test_support_ticket_emails_requester_details_to_support_inbox(self):
        self.client_user.first_name = "Boris"
        self.client_user.last_name = "User"
        self.client_user.save(update_fields=["first_name", "last_name"])
        self.authenticate(self.client_user)
        ticket = self.client.post(
            reverse("support-ticket-list"),
            {
                "subject": "Help with my listing",
                "message": "I need help updating my listing details.",
            },
            format="json",
        )

        self.assertEqual(ticket.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        support_email = mail.outbox[0]
        self.assertEqual(support_email.to, ["borisiradukunda18@gmail.com"])
        self.assertEqual(
            support_email.subject,
            "New LandLink Support Request: Help with my listing",
        )
        self.assertIn("Name: Boris User", support_email.body)
        self.assertIn("Email: client@example.com", support_email.body)
        self.assertIn("Subject: Help with my listing", support_email.body)
        self.assertIn("I need help updating my listing details.", support_email.body)

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_public_listing_feed_hides_unpublished_listings(self):
        result = self.client.get(reverse("listing-list"))
        self.assertEqual(result.status_code, 200)
        titles = [item["title"] for item in result.data["results"]]
        self.assertIn(self.listing.title, titles)
        self.assertNotIn(self.private_listing.title, titles)

    def test_listing_view_counter_is_public_and_incremented_atomically(self):
        result = self.client.post(reverse("listing-view", args=[self.listing.pk]))
        self.assertEqual(result.status_code, 204)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.views, 1)

    def test_seller_listing_is_queued_for_review(self):
        self.authenticate(self.seller)
        result = self.client.post(reverse("listing-list"), {
            "title": "New test listing",
            "description": "For review",
            "property_type": "land",
            "price_rwf": "5000000",
            "area_sqm": "250",
            "province": "Kigali City",
            "district": "Gasabo",
            "latitude": "-1.9",
            "longitude": "30.1",
        })
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["status"], Listing.Status.PENDING_REVIEW)
        self.assertFalse(result.data["is_verified"])

    def test_owner_editing_an_approved_listing_queues_it_for_review_again(self):
        self.listing.is_verified = True
        self.listing.save(update_fields=["is_verified"])
        self.authenticate(self.seller)
        result = self.client.patch(
            reverse("listing-detail", args=[self.listing.pk]),
            {"title": "Updated property information"},
            format="json",
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["status"], Listing.Status.PENDING_REVIEW)
        self.assertFalse(result.data["is_verified"])

    def test_client_cannot_create_a_property_listing(self):
        self.authenticate(self.client_user)
        result = self.client.post(reverse("listing-list"), {
            "title": "Not allowed",
            "description": "Attempt",
            "property_type": "land",
            "price_rwf": "5000000",
            "area_sqm": "250",
            "province": "Kigali City",
            "district": "Gasabo",
            "latitude": "-1.9",
            "longitude": "30.1",
        })
        self.assertEqual(result.status_code, 403)

    def test_admin_role_can_manage_listings_users_and_support_requests(self):
        admin = User.objects.create_user(
            username="role-admin@example.com",
            email="role-admin@example.com",
            password="SecurePassword123!",
            role=User.Role.ADMIN,
        )
        ticket = SupportTicket.objects.create(
            user=self.client_user,
            subject="Need help",
            message="Please review this request.",
        )
        self.authenticate(admin)

        dashboard = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["users_total"], User.objects.count())
        self.assertTrue(any(item["id"] == self.client_user.pk for item in dashboard.data["users"]))
        self.assertTrue(any(item["id"] == str(self.listing.pk) for item in dashboard.data["listings"]))
        self.assertTrue(any(item["id"] == str(ticket.pk) for item in dashboard.data["support_tickets"]))

        approved = self.client.patch(reverse("admin-dashboard"), {
            "type": "listing",
            "id": str(self.private_listing.pk),
            "decision": "approve",
        }, format="json")
        self.assertEqual(approved.status_code, 200)
        self.private_listing.refresh_from_db()
        self.assertEqual(self.private_listing.status, Listing.Status.PUBLISHED)

        not_pending = self.client.patch(reverse("admin-dashboard"), {
            "type": "listing",
            "id": str(self.listing.pk),
            "decision": "reject",
        }, format="json")
        self.assertEqual(not_pending.status_code, 400)

        suspended = self.client.patch(reverse("admin-dashboard"), {
            "type": "user",
            "id": self.client_user.pk,
            "decision": "suspend",
        }, format="json")
        self.assertEqual(suspended.status_code, 200)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.status, User.AccountStatus.SUSPENDED)

        resolved = self.client.patch(reverse("admin-dashboard"), {
            "type": "support_ticket",
            "id": str(ticket.pk),
            "decision": "resolve",
        }, format="json")
        self.assertEqual(resolved.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.RESOLVED)

    def test_public_registration_cannot_create_admin_role(self):
        result = self.client.post(reverse("register"), {
            "email": "self-promoted@example.com",
            "first_name": "Self",
            "last_name": "Promoted",
            "role": User.Role.ADMIN,
            "password": "StrongPassword123!",
        }, format="json")

        self.assertEqual(result.status_code, 400)
        self.assertFalse(User.objects.filter(email="self-promoted@example.com").exists())

    def test_provision_admin_command_creates_environment_configured_superuser(self):
        with patch.dict(os.environ, {
            "LANDLINK_ADMIN_EMAIL": "bootstrapped-admin@example.com",
            "LANDLINK_ADMIN_PASSWORD": "StrongAdminPassword123!",
        }):
            call_command("provision_admin", stdout=StringIO())

        admin = User.objects.get(email="bootstrapped-admin@example.com")
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password("StrongAdminPassword123!"))

    def test_suspended_accounts_cannot_use_protected_endpoints(self):
        self.client_user.status = User.AccountStatus.SUSPENDED
        self.client_user.save(update_fields=["status"])
        self.authenticate(self.client_user)
        self.assertEqual(self.client.get(reverse("favourite-list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("session")).status_code, 403)

    def test_client_can_create_a_survey_request_without_optional_coordinates(self):
        self.authenticate(self.client_user)
        result = self.client.post(reverse("survey-request-list"), {
            "service": "Boundary survey",
            "location": "Gasabo",
            "description": "Please survey the parcel boundary.",
            "latitude": None,
            "longitude": None,
            "desired_date": None,
            "budget_rwf": None,
        }, format="json")
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["status"], SurveyRequest.Status.OPEN)

    def test_accepting_one_quote_closes_other_quotes_and_creates_one_booking(self):
        self.authenticate(self.client_user)
        result = self.client.post(reverse("quote-accept", args=[self.quote.pk]))
        self.assertEqual(result.status_code, 201)
        self.assertEqual(Booking.objects.filter(request=self.request_obj).count(), 1)
        self.assertEqual(Quote.objects.get(pk=self.quote.pk).status, Quote.Status.ACCEPTED)
        self.assertEqual(Quote.objects.get(pk=self.second_quote.pk).status, Quote.Status.CLOSED)
        self.assertEqual(self.client.post(reverse("quote-accept", args=[self.second_quote.pk])).status_code, 400)
        self.assertEqual(Booking.objects.filter(request=self.request_obj).count(), 1)

    def test_quotes_require_an_active_authenticated_account(self):
        self.assertEqual(self.client.get(reverse("quote-list")).status_code, 401)

    def test_surveyor_must_upload_verification_document_before_admin_approval(self):
        self.surveyor_profile.verification_status = SurveyorProfile.VerificationStatus.PENDING
        self.surveyor_profile.save(update_fields=["verification_status"])
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="SecurePassword123!",
        )
        self.authenticate(admin)
        result = self.client.patch(reverse("admin-dashboard"), {
            "type": "surveyor",
            "id": str(self.surveyor_profile.pk),
            "decision": "approve",
        }, format="json")
        self.assertEqual(result.status_code, 400)
        self.surveyor_profile.refresh_from_db()
        self.assertEqual(self.surveyor_profile.verification_status, SurveyorProfile.VerificationStatus.PENDING)

    def test_surveyor_documents_are_private_and_required_for_verification(self):
        self.surveyor_profile.verification_status = SurveyorProfile.VerificationStatus.PENDING
        self.surveyor_profile.save(update_fields=["verification_status"])
        self.authenticate(self.surveyor)
        upload = SimpleUploadedFile("licence.pdf", b"%PDF-1.4\nsample document", content_type="application/pdf")
        uploaded = self.client.post(
            reverse("surveyor-document-upload"),
            {"document_type": "licence", "file": upload},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 201)
        document_id = uploaded.data["id"]
        self.assertEqual(
            self.client.get(reverse("surveyor-document-download", args=[document_id])).status_code,
            200,
        )
        other_client = User.objects.create_user(
            username="private-reader@example.com",
            email="private-reader@example.com",
            password="SecurePassword123!",
            role=User.Role.CLIENT,
        )
        self.authenticate(other_client)
        self.assertEqual(
            self.client.get(reverse("surveyor-document-download", args=[document_id])).status_code,
            403,
        )
        admin = User.objects.create_superuser(
            username="doc-admin",
            email="doc-admin@example.com",
            password="SecurePassword123!",
        )
        self.authenticate(admin)
        result = self.client.patch(reverse("admin-dashboard"), {
            "type": "surveyor",
            "id": str(self.surveyor_profile.pk),
            "decision": "approve",
        }, format="json")
        self.assertEqual(result.status_code, 200)

    def test_only_request_owner_can_accept_quote(self):
        other_client = User.objects.create_user(
            username="other-client@example.com",
            email="other-client@example.com",
            password="SecurePassword123!",
            role=User.Role.CLIENT,
        )
        self.authenticate(other_client)
        self.assertEqual(self.client.post(reverse("quote-accept", args=[self.quote.pk])).status_code, 403)

    def test_unverified_surveyor_cannot_submit_quote(self):
        pending = User.objects.create_user(
            username="pending@example.com",
            email="pending@example.com",
            password="SecurePassword123!",
            role=User.Role.SURVEYOR,
        )
        SurveyorProfile.objects.create(user=pending)
        self.authenticate(pending)
        result = self.client.post(reverse("quote-list"), {
            "request": str(self.request_obj.pk),
            "price_rwf": "200000",
            "timeline_days": 4,
            "scope_notes": "A test scope.",
        })
        self.assertEqual(result.status_code, 403)

    def test_surveyors_only_see_and_quote_requests_matching_their_service_area(self):
        outside_area = SurveyRequest.objects.create(
            client=self.client_user,
            service="Boundary survey",
            location="Musanze",
            description="A request outside the surveyor service area.",
        )
        self.authenticate(self.surveyor)
        visible = self.client.get(reverse("survey-request-list"))
        visible_ids = {item["id"] for item in visible.data["results"]}
        self.assertIn(str(self.request_obj.pk), visible_ids)
        self.assertNotIn(str(outside_area.pk), visible_ids)
        rejected = self.client.post(reverse("quote-list"), {
            "request": str(outside_area.pk),
            "price_rwf": "250000",
            "timeline_days": 5,
            "scope_notes": "A test scope.",
        }, format="json")
        self.assertEqual(rejected.status_code, 403)

    def test_unverified_surveyor_profile_is_private_to_its_owner_and_admin(self):
        pending = User.objects.create_user(
            username="private-surveyor@example.com",
            email="private-surveyor@example.com",
            password="SecurePassword123!",
            role=User.Role.SURVEYOR,
        )
        profile = SurveyorProfile.objects.create(user=pending)
        self.authenticate(self.client_user)
        self.assertEqual(
            self.client.get(reverse("surveyor-profile-detail", args=[profile.pk])).status_code,
            404,
        )
        self.authenticate(pending)
        self.assertEqual(
            self.client.get(reverse("surveyor-profile-detail", args=[profile.pk])).status_code,
            200,
        )

    def test_changing_verified_surveyor_credentials_requires_review_again(self):
        self.authenticate(self.surveyor)
        result = self.client.patch(reverse("surveyor-profile-me"), {
            "licence_number": "UPDATED-LICENCE-REF",
        }, format="json")
        self.assertEqual(result.status_code, 200)
        self.surveyor_profile.refresh_from_db()
        self.assertEqual(self.surveyor_profile.verification_status, SurveyorProfile.VerificationStatus.PENDING)

    def test_payment_cannot_be_marked_successful_without_provider(self):
        self.authenticate(self.client_user)
        result = self.client.post(reverse("payment-list"), {
            "amount_rwf": "20000",
            "purpose": "Property report",
            "status": "successful",
        })
        self.assertEqual(result.status_code, 400)

    def test_report_download_is_private_and_returns_a_pdf(self):
        self.authenticate(self.client_user)
        result = self.client.post(reverse("report-list"), {"listing": str(self.listing.pk)})
        self.assertEqual(result.status_code, 201)
        download = self.client.get(reverse("report-download", args=[result.data["id"]]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/pdf")
        self.assertTrue(download.content.startswith(b"%PDF"))
        other_user = User.objects.create_user(
            username="reader@example.com",
            email="reader@example.com",
            password="SecurePassword123!",
            role=User.Role.CLIENT,
        )
        self.authenticate(other_user)
        self.assertEqual(self.client.get(reverse("report-download", args=[result.data["id"]])).status_code, 404)
