"""
Django settings for config project.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

IS_VERCEL = os.environ.get("VERCEL") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if IS_VERCEL and not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be configured for Vercel deployments.")
SECRET_KEY = SECRET_KEY or "django-insecure-dev-key-change-before-deploy"
DEBUG = os.environ.get("DJANGO_DEBUG", "False" if IS_VERCEL else "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
    ).split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
for vercel_host_variable in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
    vercel_host = os.environ.get(vercel_host_variable)
    if vercel_host:
        ALLOWED_HOSTS.append(vercel_host)
        CSRF_TRUSTED_ORIGINS.append(f"https://{vercel_host}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "complaints",
    "ai_engine",
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

database_url = os.environ.get("DATABASE_URL")
if IS_VERCEL and not database_url:
    raise ImproperlyConfigured(
        "DATABASE_URL must point to a persistent PostgreSQL database on Vercel."
    )
if database_url or os.environ.get("DJANGO_DB_ENGINE", "sqlite").lower() in {
    "postgres",
    "postgresql",
}:
    if database_url:
        parsed_database_url = urlsplit(database_url)
        if parsed_database_url.scheme not in {"postgres", "postgresql"}:
            raise ValueError("DATABASE_URL must use the postgres or postgresql scheme.")
        database_config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed_database_url.path.lstrip("/")),
            "USER": unquote(parsed_database_url.username or ""),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname or "",
            "PORT": str(parsed_database_url.port or 5432),
            "CONN_MAX_AGE": 0 if IS_VERCEL else 60,
        }
        if parsed_database_url.query:
            database_config["OPTIONS"] = {
                key: value
                for key, value in (
                    pair.split("=", 1)
                    for pair in parsed_database_url.query.split("&")
                    if "=" in pair
                )
            }
    else:
        database_config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "civiclens"),
            "USER": os.environ.get("POSTGRES_USER", "civiclens"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    DATABASES = {
        "default": database_config,
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("DJANGO_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
media_storage_environment = {
    "bucket_name": os.environ.get("AWS_STORAGE_BUCKET_NAME"),
    "access_key": os.environ.get("AWS_ACCESS_KEY_ID"),
    "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
}
media_storage_endpoint = os.environ.get("AWS_S3_ENDPOINT_URL")
has_s3_media_storage = all(media_storage_environment.values())
if IS_VERCEL and not has_s3_media_storage:
    raise ImproperlyConfigured(
        "Configure an S3-compatible media bucket on Vercel; function filesystems "
        "are not persistent."
    )
STORAGES = {
    "default": (
        {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                **media_storage_environment,
                "region_name": os.environ.get(
                    "AWS_S3_REGION_NAME", "auto" if media_storage_endpoint else "us-east-1"
                ),
                **(
                    {"endpoint_url": media_storage_endpoint}
                    if media_storage_endpoint
                    else {}
                ),
            },
        }
        if has_s3_media_storage
        else {"BACKEND": "django.core.files.storage.FileSystemStorage"}
    ),
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "False").lower() == "true"
SECURE_COOKIES = os.environ.get("DJANGO_SECURE_COOKIES", str(not DEBUG)).lower() == "true"
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
