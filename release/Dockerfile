# Keep the test/release runtime aligned with the production image.  asyncmy
# publishes a Linux wheel for CPython 3.12, so no gcc toolchain is required.
FROM python:3.12-slim AS python-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
WORKDIR /app
ARG DEBIAN_MIRROR=deb.debian.org
RUN sed -i "s|deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
  && apt-get update \
  && apt-get install --no-install-recommends -y ffmpeg \
  && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM python-base AS test
COPY backend/requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY backend/ /app/backend/
ENV PYTHONPATH=/app/backend \
    APP_ENV=test \
    APP_SECRET_KEY=test-secret-key-that-is-longer-than-32-bytes \
    MODEL_CREDENTIAL_ENCRYPTION_KEY=test-model-key-that-is-longer-than-32-bytes \
    SERVICE_API_KEY_PEPPER=test-api-pepper-that-is-longer-than-32-bytes \
    RESULT_DOWNLOAD_SIGNING_KEY=test-download-key-that-is-longer-than-32-bytes \
    DATABASE_URL=sqlite+aiosqlite:////tmp/zhilian-service-platform-test.db \
    ADMIN_INITIAL_USERNAME=admin \
    ADMIN_INITIAL_PASSWORD=development-password
WORKDIR /app

FROM python-base AS release
RUN addgroup --system app && adduser --system --ingroup app app
COPY backend/app /app/app
COPY backend/migrations /app/migrations
COPY backend/alembic.ini /app/alembic.ini
COPY backend/entrypoint.py /app/entrypoint.py
COPY frontend/dist /app/app/static
RUN chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["python", "/app/entrypoint.py"]
