"""Isolated checks; never use the live database or authorize real invoices."""
import os
from .settings import *  # noqa: F403

SECRET_KEY = 'devlink-isolated-billing-tests-only'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
BILLING_ALLOW_PRODUCTION = False
BILLING_NETWORK_ENABLED = False
if os.environ.get('BILLING_TEST_POSTGRES') != '1':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
