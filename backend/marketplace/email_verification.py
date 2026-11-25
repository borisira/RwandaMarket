import smtplib

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


class EmailDeliveryError(Exception):
    pass


def email_verification_enabled():
    return bool(
        settings.EMAIL_HOST
        and settings.EMAIL_HOST_USER
        and settings.EMAIL_HOST_PASSWORD
        and settings.DEFAULT_FROM_EMAIL
    )


def send_verification_email(user, verification_url):
    if not email_verification_enabled():
        raise EmailDeliveryError("SMTP credentials are not configured.")

    context = {
        "first_name": user.first_name or "there",
        "verification_url": verification_url,
    }
    message = EmailMultiAlternatives(
        subject="Welcome to LandLink — verify your email",
        body=render_to_string("emails/verification.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(
        render_to_string("emails/verification.html", context),
        "text/html",
    )

    try:
        sent = message.send(fail_silently=False)
    except (OSError, smtplib.SMTPException, TimeoutError, ValueError) as exc:
        raise EmailDeliveryError("The SMTP server did not accept the request.") from exc

    if sent != 1:
        raise EmailDeliveryError("The SMTP server did not accept the recipient.")
