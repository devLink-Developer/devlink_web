"""Session locks outlive the fiscal transaction and end with the worker connection."""
from contextlib import contextmanager
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection


@contextmanager
def configuration_operation(configuration_id):
    if connection.vendor != 'postgresql':
        if settings.BILLING_NETWORK_ENABLED:
            raise ValidationError('La operación fiscal requiere PostgreSQL para proteger los envíos concurrentes.')
        yield
        return
    # Separate namespace from every other application's advisory locks.
    # One issuer is supported. A single issuer-wide key also protects a CUIT edit
    # in another environment from racing with a first authorization.
    key = (0x444C << 32) + 1
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s)', [key])
        acquired = cursor.fetchone()[0]
    if not acquired:
        raise ValidationError('Hay una operación activa en este ambiente. Esperá a que termine antes de emitir, conciliar o cambiar la configuración.')
    physical_connection = connection.connection
    try:
        yield
    finally:
        if connection.connection is physical_connection and connection.is_usable():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(%s)', [key])
