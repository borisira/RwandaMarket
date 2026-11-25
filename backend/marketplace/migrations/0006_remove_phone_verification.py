from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0005_phoneverification_email_attempts_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="phone_number",
        ),
        migrations.RemoveField(
            model_name="user",
            name="phone_verified_at",
        ),
        migrations.DeleteModel(
            name="PhoneVerification",
        ),
    ]
