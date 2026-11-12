FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Prepare writable runtime directories before copying source with its owner.
RUN adduser --disabled-password --gecos '' appuser
RUN mkdir -p /app/staticfiles /home/appuser/.local/share/devlink/invoices \
    && chown appuser:appuser /app /app/staticfiles \
    && chown -R appuser:appuser /home/appuser/.local
COPY --chown=appuser:appuser . .
USER appuser

# Static assets are created by their final runtime owner, avoiding a recursive
# ownership rewrite of the entire application and generated static tree.
RUN python manage.py collectstatic --noinput

EXPOSE 8002

CMD ["gunicorn", "--bind", "0.0.0.0:8002", "--workers", "3", "devlink_web.wsgi:application"]
