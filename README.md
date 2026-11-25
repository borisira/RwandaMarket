# LandLink

A land and home marketplace with a Django REST API and a Vue 3 + TypeScript frontend. It includes listing moderation, surveyor verification, quote-to-booking workflows, reviews, property-report previews, support and an admin audit trail.

## Run locally (Windows)

Requirements: Python 3.10+ and Node.js 20+.

1. Use `backend\.env.example` as the template for `backend\.env` and fill in the credentials. If `backend\.env` already exists, merge the keys without overwriting its current values. Registration requires SMTP delivery to be configured; the example values do not enable delivery.
2. Install backend dependencies and initialise the local SQLite database:

   ```powershell
   python -m pip install -r backend\requirements.txt
   python backend\manage.py migrate
   ```

3. Start Django in one terminal:

   ```powershell
   python backend\manage.py runserver 127.0.0.1:8000
   ```

4. In a second terminal, install frontend dependencies and start Vite:

   ```powershell
   Set-Location frontend
   npm install
   npm run dev
   ```

5. Open <http://127.0.0.1:5173>. To moderate listings or surveyor profiles, create a Django administrator with `python backend\manage.py createsuperuser`, sign in to the app with that account, then open the Admin dashboard.

Listing location selectors use the Rwanda province-to-village hierarchy from [rwanda-geo](https://github.com/Monehin/rwanda-geo), distributed under the MIT license included in [frontend/src/data/LICENSE.rwanda-geo](frontend/src/data/LICENSE.rwanda-geo). Listing photos support up to 10 JPEG, PNG or WebP images (5 MB each).

## Account verification and email

New accounts remain pending until the user clicks the verification link sent to their email address. The branded HTML email includes a plain-text alternative, and its signed link expires after 24 hours. If SMTP delivery fails during registration, the pending account is removed. Set `FRONTEND_URL` to the public frontend origin so successful verification returns users to the app.

## Admin account provisioning

Admin accounts cannot be created through public registration. After migrations, set `LANDLINK_ADMIN_EMAIL` and `LANDLINK_ADMIN_PASSWORD` in the deployment environment and run `python backend\manage.py provision_admin`. This creates or promotes the configured account with Django admin access. Keep the password in a secret manager or local environment only; never commit it.

For Gmail SMTP, enable two-step verification and create an app password. Put that app password in `EMAIL_HOST_PASSWORD`; do not use your normal Gmail password. Use the provider's corresponding host, port and TLS settings if you use another SMTP service. Never commit `backend\.env` or share its secrets.

The local database is SQLite for development. Before production, configure PostgreSQL, strong secrets and HTTPS, private object storage, SMTP, deployment-specific rate limits, monitoring and backups. Maps use OpenStreetMap street tiles and show seller-provided pins only. No official UPI, cadastral, boundary or Master Plan data is fabricated; reports are explicitly marked previews, and payment creation is disabled.

## Backend checks

```powershell
python backend\manage.py test marketplace
python backend\manage.py check
```

## API areas

- `/api/auth/register/`, `/api/auth/login/`, `/api/auth/me/`
- `/api/auth/email/verify/`
- `/api/listings/`, `/api/favourites/`, `/api/enquiries/`
- `/api/surveyor-profiles/`, `/api/survey-requests/`, `/api/quotes/`, `/api/bookings/`, `/api/reviews/`
- `/api/reports/`, `/api/payments/`, `/api/complaints/`, `/api/support-tickets/`, `/api/notifications/`
- `/api/admin/dashboard/` and Django's `/admin/`
