#!/usr/bin/env bash
# Start all infrastructure and the API server for local development
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Starting Docker services (postgres, redis, minio, clamav)..."
docker compose up -d postgres redis minio clamav

echo "==> Running MinIO bucket init..."
docker compose run --rm minio-init > /dev/null 2>&1 || true

echo "==> Waiting for postgres..."
until docker compose exec -T postgres pg_isready -U pdfkit > /dev/null 2>&1; do
  sleep 1
done
echo "    postgres ready"

echo "==> Installing backend dependencies..."
cd "$ROOT/backend"
pip3 install -q -r requirements.txt

echo "==> Starting FastAPI..."
set -a; source "$ROOT/.env"; set +a
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "==> Starting Celery worker (default queue)..."
PYTHONPATH=. celery -A app.workers.celery_app worker -Q default -c 2 --loglevel=warning &
CELERY_PID=$!

echo "==> Starting Celery worker (ocr queue)..."
PYTHONPATH=. celery -A app.workers.celery_app worker -Q ocr,ai -c 1 --loglevel=warning &
CELERY_OCR_PID=$!

echo ""
echo "  API:        http://localhost:8000"
echo "  Docs:       http://localhost:8000/api/docs"
echo "  MinIO UI:   http://localhost:9001  (minioadmin / minioadmin)"
echo "  Frontend:   cd frontend && npm run dev"
echo ""
echo "Press Ctrl+C to stop all"

trap "kill $API_PID $CELERY_PID $CELERY_OCR_PID 2>/dev/null; docker compose stop" INT TERM
wait
