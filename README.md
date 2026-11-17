# O.M.N RwandaMarket

A responsive land and home marketplace with a Django REST API and a Vue 3 + TypeScript frontend. It includes listing moderation, surveyor verification, quote-to-booking workflows, reviews, property-report previews, support and an admin audit trail.

## Run locally (Windows)

Requirements: Python 3.10+ and Node.js 20+.

Backend settings are read from `backend\.env`; the frontend reads `frontend\.env`. Both files have local-development defaults and should not be committed.
Listing location selectors use the Rwanda province-to-village hierarchy from [rwanda-geo](https://github.com/Monehin/rwanda-geo), distributed under the MIT license included in [frontend/src/data/LICENSE.rwanda-geo](frontend/src/data/LICENSE.rwanda-geo). Listing photos are uploaded after the listing form, with up to 10 JPEG, PNG or WebP images (5 MB each).

1. In PowerShell, install backend dependencies and initialise the local SQLite database:

   ```powershell
   python -m pip install -r backend\requirements.txt
   python backend\manage.py migrate
   python backend\manage.py seed_demo
   ```

2. Start Django in one terminal:

   ```powershell
   python backend\manage.py runserver 127.0.0.1:8000
   ```

3. In a second terminal, install frontend dependencies and start Vite:

   ```powershell
   Set-Location frontend
   npm install
   npm run dev
   ```

4. Open <http://127.0.0.1:5173>. To moderate listings or surveyor profiles, create a Django administrator with `python backend\manage.py createsuperuser`, sign in to the app with that account, then open the Admin dashboard.

Sample listings are visibly marked as examples and use no real seller account credentials. To create listings, register a seller account; to request surveys, register a client account. Surveyor quotes are available only after an administrator approves a surveyor profile. Review the data and workflow before treating any sample output as real.

## Included workflows

- Browse, filter and search published land and house listings; send seller enquiries; save favourites; report a listing.
- Seller registration and listing submission; new listings remain private until reviewed by an administrator.
- Surveyor registration and profile editing; profiles are hidden until an administrator verifies them.
- Client survey requests, verified-surveyor quotes, single-quote acceptance, booking status transitions, report delivery and completed-booking reviews.
- Interactive OpenStreetMap view, coordinate search, current-location permission, Google Maps / Earth links and shareable coordinates.
- Private, owner-scoped Property Insight Report PDF previews.
- Support tickets, complaints, in-app notifications and Django admin records.
- Kinyarwanda, English and French interface selection, remembered locally and in a signed-in profile.

## External services and launch limitations

The project guide leaves provider, pricing, legal and data-rights decisions open. This build does **not** make up official UPI, cadastral, boundary or Master Plan data. Maps use OpenStreetMap street tiles and show seller-provided pins only. Satellite imagery and authoritative zoning remain unavailable until a licensed provider and official data source are selected. Property reports are explicitly marked previews. Payment creation is disabled and no payment can be marked successful in this build. Email/SMS delivery, OTP verification, private document uploads, paid subscriptions and production file storage also need approved providers before launch.

The local database is SQLite for easy setup. Before production, configure PostgreSQL/PostGIS, production secrets and HTTPS, private object storage, verified email/phone delivery, an approved payment gateway, official GIS data and a licensed satellite map provider. Add deployment-specific rate limits, monitoring, backups, reviewed legal texts and human-checked translations; the demo defaults are not production security settings.

## Backend checks

```powershell
python backend\manage.py test marketplace
python backend\manage.py check
```

## API areas

- `/api/auth/register/`, `/api/auth/login/`, `/api/auth/me/`
- `/api/listings/`, `/api/favourites/`, `/api/enquiries/`
- `/api/surveyor-profiles/`, `/api/survey-requests/`, `/api/quotes/`, `/api/bookings/`, `/api/reviews/`
- `/api/reports/`, `/api/payments/`, `/api/complaints/`, `/api/support-tickets/`, `/api/notifications/`
- `/api/admin/dashboard/` and Django's `/admin/`
