"""Production settings — used on the real server.

Selected with ``DJANGO_SETTINGS_MODULE=config.settings.production`` (set in
.env.production / the production docker-compose). Values that differ per
deployment are read from environment variables.
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

# Comma-separated lists in the environment, e.g.
#   ALLOWED_HOSTS=tbsmrd.local,192.168.1.50
#   CSRF_TRUSTED_ORIGINS=http://tbsmrd.local,http://192.168.1.50
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Never ship the development fallback key to a real server.
if SECRET_KEY == "unsafe-secret":
    raise ImproperlyConfigured("SECRET_KEY must be set in the production environment.")

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set in the production environment.")

# --- Static files via WhiteNoise (served by the app, no separate nginx needed) ---
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- Security hardening ---
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HTTPS-specific flags. Default OFF because an internal server is often plain
# HTTP; turn each on via the environment once TLS is terminated in front.
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False") == "True"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False") == "True"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False") == "True"
# Trust the X-Forwarded-Proto header when running behind a TLS-terminating proxy.
if os.getenv("USE_FORWARDED_PROTO", "False") == "True":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
