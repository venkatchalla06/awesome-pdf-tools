FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-eng \
    libmagic1 \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-calc \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS production
COPY . .

# Non-root user for security
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/uploads /tmp/pdf-work \
    && chown -R appuser:appuser /app /tmp/pdf-work
USER appuser

# Default command is the API server; workers override this in docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
