import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone


class Command(BaseCommand):
    help = "Create or promote the configured LandLink admin account."

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.environ.get("LANDLINK_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("LANDLINK_ADMIN_PASSWORD", "")
        if not email:
            raise CommandError("Set LANDLINK_ADMIN_EMAIL before provisioning an admin.")

        user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
        if user is None:
            if not password:
                raise CommandError("Set LANDLINK_ADMIN_PASSWORD to create the admin account.")
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                role=User.Role.ADMIN,
                status=User.AccountStatus.ACTIVE,
                is_active=True,
                is_staff=True,
                is_superuser=True,
                is_verified=True,
                email_verified_at=timezone.now(),
            )
            self.stdout.write(self.style.SUCCESS(f"Created admin account for {email}."))
            return

        if user.email.casefold() != email:
            raise CommandError("That username already belongs to an account with a different email.")
        user.role = User.Role.ADMIN
        user.status = User.AccountStatus.ACTIVE
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.is_verified = True
        if user.email_verified_at is None:
            user.email_verified_at = timezone.now()
        user.save(update_fields=[
            "role", "status", "is_active", "is_staff", "is_superuser",
            "is_verified", "email_verified_at",
        ])
        self.stdout.write(self.style.SUCCESS(f"Promoted existing account {email} to admin."))
