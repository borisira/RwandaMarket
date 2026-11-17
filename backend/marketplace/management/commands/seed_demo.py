from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from marketplace.models import Listing


class Command(BaseCommand):
    help = "Create clearly labelled sample listings for local development."

    def handle(self, *args, **options):
        if Listing.objects.exists():
            self.stdout.write(self.style.WARNING("Listings already exist; no sample data was changed."))
            return

        User = get_user_model()
        seller, created = User.objects.get_or_create(
            username="demo.seller@example.com",
            defaults={
                "email": "demo.seller@example.com",
                "first_name": "Demo",
                "last_name": "Seller",
                "role": User.Role.SELLER,
                "language": User.Language.EN,
            },
        )
        if created:
            seller.set_unusable_password()
            seller.save(update_fields=["password"])

        examples = [
            {
                "title": "[Sample] Residential plot near Kimironko",
                "description": "Illustrative development data for local testing only. This is not a real property offer and has not been independently verified.",
                "property_type": Listing.PropertyType.LAND,
                "price_rwf": 42000000,
                "area_sqm": 420,
                "province": "Kigali City",
                "district": "Gasabo",
                "sector": "Kimironko",
                "latitude": -1.9292,
                "longitude": 30.1241,
                "photo_url": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1000&q=82",
            },
            {
                "title": "[Sample] Family home in Kicukiro",
                "description": "Illustrative development data for local testing only. This is not a real property offer and has not been independently verified.",
                "property_type": Listing.PropertyType.HOUSE,
                "price_rwf": 118000000,
                "area_sqm": 186,
                "province": "Kigali City",
                "district": "Kicukiro",
                "sector": "Niboye",
                "latitude": -2.0069,
                "longitude": 30.1084,
                "photo_url": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1000&q=82",
            },
            {
                "title": "[Sample] Hillside land in Musanze",
                "description": "Illustrative development data for local testing only. This is not a real property offer and has not been independently verified.",
                "property_type": Listing.PropertyType.LAND,
                "price_rwf": 28500000,
                "area_sqm": 600,
                "province": "Northern Province",
                "district": "Musanze",
                "sector": "Muhoza",
                "latitude": -1.4997,
                "longitude": 29.6343,
                "photo_url": "https://images.unsplash.com/photo-1510798831971-661eb04b3739?auto=format&fit=crop&w=1000&q=82",
            },
        ]
        for data in examples:
            Listing.objects.create(owner=seller, status=Listing.Status.PUBLISHED, **data)
        self.stdout.write(self.style.SUCCESS(f"Created {len(examples)} explicitly marked sample listings."))
