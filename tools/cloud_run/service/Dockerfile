# Admin API + static dashboard (Cloud Run Service)
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    JOB_MODE=cloud \
    APP_ROOT=/app \
    ASSETS_DIR=/app/assets \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8080 \
    ADMIN_STATIC_DIR=/app/website/admin

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

COPY tools/cloud_run/requirements.txt /tmp/requirements-cloud-run.txt
COPY tools/gmail/requirements.txt /tmp/requirements-gmail.txt
RUN pip install --no-cache-dir \
    -r /tmp/requirements-cloud-run.txt \
    -r /tmp/requirements-gmail.txt \
    && playwright install chromium

COPY tools/gmail/auth.py tools/gmail/scanner.py tools/gmail/storage.py tools/gmail/job_runner.py /app/gmail/
COPY tools/cloud_run/ /app/cloud_run/
COPY base/cary_jones_resume.html /app/assets/cary_jones_resume.html
COPY website/contact.json /app/assets/contact.json
COPY applications/weave/resume.html /app/assets/examples/weave/resume.html
COPY website/admin/ /app/website/admin/

WORKDIR /app/cloud_run
CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8080"]
