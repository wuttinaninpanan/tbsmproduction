"""Development settings — used on developer machines.

Selected via ``DJANGO_SETTINGS_MODULE=config.settings.local`` (the default in
manage.py / wsgi.py / asgi.py and in .env.local).
"""
from .base import *  # noqa: F401,F403

# Convenient for local work — never use these on the real server.
DEBUG = True
ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "http://172.29.66.227:8003",
    "https://172.29.66.227:8003",
    "http://172.29.66.227",
    "https://172.29.66.227",
    "https://tapeless-joseph-fallalishly.ngrok-free.dev",
    "http://tapeless-joseph-fallalishly.ngrok-free.dev",
]
