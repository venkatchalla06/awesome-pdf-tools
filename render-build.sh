#!/usr/bin/env bash
set -e

# Install system dependencies (best-effort — may not all be available)
apt-get update -qq && apt-get install -y -qq \
    ghostscript tesseract-ocr tesseract-ocr-eng \
    libmagic1 poppler-utils 2>/dev/null || true

# Install Python dependencies
pip install -r requirements.txt

# Create upload dirs
mkdir -p /tmp/pdf-toolkit/uploads
