from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0006_remove_phone_verification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("client", "Client / buyer"),
                    ("seller", "Seller / agent"),
                    ("surveyor", "Surveyor"),
                    ("admin", "Admin"),
                ],
                default="client",
                max_length=16,
            ),
        ),
    ]
