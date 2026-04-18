# APEPDCL PDF Tools — Production Deployment Guide

## Overview

The application runs entirely in Docker Compose and consists of 10 containers:

| Container | Role |
|---|---|
| `postgres` | PostgreSQL 16 database |
| `redis` | Redis 7 — task queue & rate limiting |
| `minio` | S3-compatible file storage |
| `minio-init` | Creates the storage bucket on first run |
| `clamav` | Antivirus scanning |
| `api` | FastAPI backend (port 8000 internally) |
| `worker` | Celery worker — PDF processing tasks |
| `worker-ocr` | Celery worker — OCR & AI tasks |
| `beat` | Celery beat — scheduled cleanup |
| `frontend` | Next.js frontend (port 3000 internally) |
| `nginx` | Reverse proxy — public entry point (port 80) |

---

## Step 1 — Server Requirements

**Minimum production server:**
- OS: Ubuntu 22.04 LTS or Debian 12
- CPU: 4 cores
- RAM: 8 GB (16 GB recommended for AI tools)
- Disk: 50 GB SSD
- Docker Engine: 24+
- Docker Compose: 2.20+

**Install Docker on Ubuntu:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

---

## Step 2 — Copy the Project to the Server

**Option A — from your local machine:**
```bash
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
  /Users/venkat/Projects/pdfkit/ user@YOUR_SERVER_IP:/opt/pdfkit/
```

**Option B — from Git:**
```bash
git clone https://your-repo-url.git /opt/pdfkit
cd /opt/pdfkit
```

---

## Step 3 — Configure Environment Variables

Copy the example env file and edit it:

```bash
cd /opt/pdfkit
cp .env .env.production
nano .env.production
```

**Production `.env` file — fill in all values:**

```env
# ── Application ────────────────────────────────────────────
DEBUG=false
SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING_64_CHARS

# ── Database ────────────────────────────────────────────────
POSTGRES_DB=pdfkit
POSTGRES_USER=pdfkit
POSTGRES_PASSWORD=CHANGE_THIS_STRONG_DB_PASSWORD

DATABASE_URL=postgresql+asyncpg://pdfkit:CHANGE_THIS_STRONG_DB_PASSWORD@postgres:5432/pdfkit

# ── Redis ───────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ── File Storage (MinIO) ────────────────────────────────────
S3_BUCKET=pdfkit
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=CHANGE_THIS_MINIO_USER
AWS_SECRET_ACCESS_KEY=CHANGE_THIS_MINIO_PASSWORD

# Internal URL used by workers
S3_ENDPOINT_URL=http://minio:9000

# Public URL used by browsers to upload/download files
# Set this to your server's public IP or domain
S3_PUBLIC_URL=http://YOUR_SERVER_IP:9002

# ── ClamAV ──────────────────────────────────────────────────
CLAMAV_HOST=clamav

# ── AI (Ollama) ─────────────────────────────────────────────
# If running Ollama on the host machine:
OLLAMA_URL=http://host.docker.internal:11434

# ── Temp file TTL ───────────────────────────────────────────
TEMP_FILE_TTL_HOURS=2
```

**Generate a secure SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 4 — Update nginx for Your Domain

Edit `nginx/nginx.conf` and set your domain:

```bash
nano /opt/pdfkit/nginx/nginx.conf
```

Change `server_name _;` to your domain:
```nginx
server_name pdftools.apepdcl.in;
```

If you are **not** using HTTPS yet, keep port 80. For HTTPS see Step 8.

---

## Step 5 — Update Public URLs in docker-compose.yml

Open `docker-compose.yml` and update the public MinIO URL:

```bash
nano /opt/pdfkit/docker-compose.yml
```

Change this line in the `api` service:
```yaml
- S3_PUBLIC_URL=http://YOUR_SERVER_IP:9002
```

Also expose MinIO port 9002 publicly (already in the file):
```yaml
minio:
  ports:
    - "9002:9000"   # Browser upload target — must be reachable from users' browsers
    - "9001:9001"   # MinIO admin console — restrict in firewall
```

---

## Step 6 — Build and Start All Services

```bash
cd /opt/pdfkit

# Build all Docker images (takes 5–10 minutes on first run)
docker compose --env-file .env.production build

# Start everything in background
docker compose --env-file .env.production up -d

# Watch startup logs
docker compose --env-file .env.production logs -f
```

Wait until you see:
```
pdfkit-api-1       | INFO: Application startup complete.
pdfkit-worker-1    | celery@... ready.
pdfkit-worker-ocr-1| celery@... ready.
```

---

## Step 7 — Run Database Migrations

The database tables are created automatically on API startup via SQLAlchemy. Verify:

```bash
docker exec pdfkit-postgres-1 psql -U pdfkit -d pdfkit -c "\dt"
```

Expected tables: `users`, `jobs`

If the `tooltype` enum is missing new values, run:
```bash
docker exec pdfkit-postgres-1 psql -U pdfkit -d pdfkit -c "
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'REMOVE_PAGES';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'EXTRACT_PAGES';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'REPAIR';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'CROP';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'PPTX_TO_PDF';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'XLSX_TO_PDF';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'HTML_TO_PDF';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'REDACT';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'PDF_TO_PDFA';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'ORGANIZE';
ALTER TYPE tooltype ADD VALUE IF NOT EXISTS 'PDF_TO_PPTX';
"
```

---

## Step 8 — Verify Everything is Running

```bash
# Check all containers are up
docker compose --env-file .env.production ps

# Expected: all 10 containers should show "running" or "healthy"

# Test API health
curl http://localhost:9000/health
# Expected: {"status":"ok","version":"1.0.0"}

# Test homepage
curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/
# Expected: 200
```

---

## Step 9 — Configure Firewall

Allow only the ports you need:

```bash
# Allow HTTP (app)
sudo ufw allow 80/tcp

# Allow HTTPS (if using SSL)
sudo ufw allow 443/tcp

# Allow MinIO for browser uploads (required!)
sudo ufw allow 9002/tcp

# Block MinIO admin console from public (optional — access only internally)
sudo ufw deny 9001/tcp

# Block direct API port
sudo ufw deny 8000/tcp

sudo ufw enable
sudo ufw status
```

---

## Step 10 — HTTPS with Let's Encrypt (Recommended)

Install Certbot:
```bash
sudo apt install certbot python3-certbot-nginx -y
```

Stop nginx container temporarily:
```bash
docker compose --env-file .env.production stop nginx
```

Get certificate:
```bash
sudo certbot certonly --standalone -d pdftools.apepdcl.in
```

Update `nginx/nginx.conf` to add HTTPS:
```nginx
server {
    listen 80;
    server_name pdftools.apepdcl.in;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name pdftools.apepdcl.in;

    ssl_certificate     /etc/letsencrypt/live/pdftools.apepdcl.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pdftools.apepdcl.in/privkey.pem;

    client_max_body_size 110M;
    proxy_read_timeout    300s;
    proxy_send_timeout    300s;
    proxy_connect_timeout 60s;

    location /api/ {
        proxy_pass http://api;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://api/health;
    }

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";
    }
}
```

Mount SSL certs into the nginx container in `docker-compose.yml`:
```yaml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

Restart nginx:
```bash
docker compose --env-file .env.production up -d nginx
```

---

## Step 11 — Install Ollama for AI Tools (Optional)

AI tools (Summarize, Translate) require Ollama running on the host:

```bash
# Install Ollama on the host server
curl -fsSL https://ollama.com/install.sh | sh

# Pull the AI model (requires ~5 GB disk)
ollama pull gemma3:4b

# Verify it's running
curl http://localhost:11434/api/tags
```

The `worker-ocr` container connects to Ollama via `host.docker.internal:11434`. This is already configured in `docker-compose.yml`.

---

## Step 12 — Set Up Auto-restart on Server Reboot

```bash
# Enable Docker to start on boot
sudo systemctl enable docker

# Create a systemd service for the app
sudo tee /etc/systemd/system/pdfkit.service > /dev/null <<EOF
[Unit]
Description=APEPDCL PDF Tools
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/pdfkit
ExecStart=/usr/bin/docker compose --env-file .env.production up -d
ExecStop=/usr/bin/docker compose --env-file .env.production down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pdfkit
```

---

## Useful Commands

```bash
# View all container status
docker compose --env-file .env.production ps

# View logs for a specific service
docker compose --env-file .env.production logs -f api
docker compose --env-file .env.production logs -f worker

# Restart a single service
docker compose --env-file .env.production restart api

# Stop everything
docker compose --env-file .env.production down

# Stop and delete all data (CAUTION — deletes database)
docker compose --env-file .env.production down -v

# Update app after code changes
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d

# Access PostgreSQL directly
docker exec -it pdfkit-postgres-1 psql -U pdfkit -d pdfkit

# Access Redis
docker exec -it pdfkit-redis-1 redis-cli

# Clear rate limits manually
docker exec pdfkit-redis-1 sh -c 'redis-cli KEYS "rl:*" | xargs -r redis-cli DEL'

# MinIO admin console
# Open in browser: http://YOUR_SERVER_IP:9001
# Login: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from .env
```

---

## Troubleshooting

**Nginx 502 Bad Gateway after restart:**
```bash
# API container IP changed — restart nginx to refresh DNS
docker compose --env-file .env.production restart nginx
```

**File uploads failing (browser can't reach MinIO):**
- Ensure port 9002 is open in firewall
- Ensure `S3_PUBLIC_URL` in `.env` is set to server's public IP/domain
- MinIO must be accessible from users' browsers

**AI tools failing:**
- Ensure Ollama is running: `systemctl status ollama`
- Ensure model is pulled: `ollama list`
- Check worker-ocr logs: `docker compose logs worker-ocr`

**Jobs stuck in pending:**
```bash
# Check worker is running and connected
docker compose --env-file .env.production logs worker
# Look for: "celery@... ready"
```

**Database enum error on new tools:**
```bash
# Run the ALTER TYPE commands from Step 7
docker exec pdfkit-postgres-1 psql -U pdfkit -d pdfkit -c "\dT+ tooltype"
```

---

## Verified Tool List (25 tools — all passing)

| Category | Tools |
|---|---|
| Organize | Merge, Split, Remove Pages, Extract Pages, Organize, Rotate, Page Numbers |
| Optimize | Compress, Repair |
| Convert from PDF | PDF to Word, PDF to JPG, PDF to PDF/A |
| Convert to PDF | Word, JPG, PowerPoint, Excel, HTML |
| Edit | Watermark, Crop, Redact |
| Security | Protect, Unlock |
| AI | OCR, AI Summarize, AI Translate |

**All 25 tools tested and verified: READY FOR PRODUCTION**
