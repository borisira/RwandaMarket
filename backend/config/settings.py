import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY in the environment.")

debug_value = os.environ.get("DJANGO_DEBUG", "false").strip().lower()
if debug_value not in {"true", "false"}:
    raise ImproperlyConfigured("DJANGO_DEBUG must be 'true' or 'false'.")
DEBUG = debug_value == "true"
allowed_hosts_setting = os.environ.get("DJANGO_ALLOWED_HOSTS")
ALLOWED_HOSTS = [
    host.strip()
    for host in (allowed_hosts_setting or "localhost,127.0.0.1").split(",")
    if host.strip()
]

if not DEBUG:
    if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
        raise ImproperlyConfigured("Set a strong, randomly generated DJANGO_SECRET_KEY for production.")
    if not allowed_hosts_setting or not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Set explicit production hosts in DJANGO_ALLOWED_HOSTS.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "marketplace",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    database_url = urlparse(DATABASE_URL)
    if database_url.scheme not in {"postgres", "postgresql"} or not database_url.hostname or not database_url.path.strip("/"):
        raise ImproperlyConfigured("DATABASE_URL must be a valid PostgreSQL connection URL.")
    query = parse_qs(database_url.query)
    database_options = {"sslmode": query.get("sslmode", ["require" if not DEBUG else "prefer"])[0]}
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(database_url.path.lstrip("/")),
            "USER": unquote(database_url.username or ""),
            "PASSWORD": unquote(database_url.password or ""),
            "HOST": database_url.hostname,
            "PORT": database_url.port or 5432,
            "CONN_MAX_AGE": 60,
            "OPTIONS": database_options,
        }
    }
else:
    if not DEBUG:
        raise ImproperlyConfigured("Set DATABASE_URL to a persistent PostgreSQL database for production.")
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_USER_MODEL = "marketplace.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Kigali"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = os.environ.get(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()]
if not DEBUG and not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured("Set the production frontend origin in DJANGO_CORS_ALLOWED_ORIGINS.")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if not DEBUG else None
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "10/hour",
        "auth_login": "20/minute",
        "email_verify": "20/hour",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com").strip()
try:
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
except ValueError as exc:
    raise ImproperlyConfigured("EMAIL_PORT must be an integer.") from exc
if not 1 <= EMAIL_PORT <= 65535:
    raise ImproperlyConfigured("EMAIL_PORT must be between 1 and 65535.")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "").strip()
email_use_tls = os.environ.get("EMAIL_USE_TLS", "true").strip().lower()
email_use_ssl = os.environ.get("EMAIL_USE_SSL", "false").strip().lower()
if email_use_tls not in {"true", "false"} or email_use_ssl not in {"true", "false"}:
    raise ImproperlyConfigured("EMAIL_USE_TLS and EMAIL_USE_SSL must be 'true' or 'false'.")
EMAIL_USE_TLS = email_use_tls == "true"
EMAIL_USE_SSL = email_use_ssl == "true"
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("Set only one of EMAIL_USE_TLS and EMAIL_USE_SSL.")
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER).strip()
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    CORS_ALLOWED_ORIGINS[0] if CORS_ALLOWED_ORIGINS else "http://localhost:5173",
).strip().rstrip("/")

if not DEBUG:
    if not EMAIL_HOST or not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD or not DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured("Configure SMTP email credentials before running production.")
    if not EMAIL_USE_TLS and not EMAIL_USE_SSL:
        raise ImproperlyConfigured("Use TLS or SSL for production SMTP.")
