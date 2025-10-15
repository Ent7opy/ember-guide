# EmberGuide Deployment Guide

Production deployment instructions for running EmberGuide in a reliable, scalable environment.

---

## Overview

EmberGuide consists of three main components:
1. **Pipeline** (batch processing): Runs on schedule to generate nowcasts
2. **API** (FastAPI backend): Serves GeoTIFFs, tiles, and metadata
3. **UI** (Streamlit frontend): Interactive web interface

This guide covers:
- Server requirements
- Docker containerization
- Environment configuration
- Reverse proxy setup (nginx)
- Monitoring and logging
- Backup and disaster recovery

---

## Server Requirements

### Minimum Specifications

**Pipeline Server**:
- CPU: 4+ cores (8+ recommended for parallel processing)
- RAM: 16 GB (32 GB for large fires)
- Storage: 500 GB SSD (for data caching)
- Network: Reliable internet (for downloading FIRMS/ERA5 data)

**API + UI Server**:
- CPU: 2+ cores
- RAM: 8 GB
- Storage: 100 GB SSD (for products only)
- Network: Good bandwidth (serving tiles)

**Note**: Pipeline and API/UI can run on the same server for small deployments.

### Software Requirements

- **OS**: Ubuntu 22.04 LTS or similar Linux
- **Python**: 3.11+
- **Docker**: 20.10+ (optional but recommended)
- **Nginx**: 1.18+ (reverse proxy)
- **Git**: Version control

---

## Architecture Options

### Option 1: Single Server (Small Scale)

```
┌─────────────────────────────────────┐
│         Single Server               │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  Pipeline    │  │  API + UI   │ │
│  │  (cron)      │─▶│  (Docker)   │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  data/                      │   │
│  │  ├── raw/                   │   │
│  │  ├── interim/               │   │
│  │  └── products/ (shared)     │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
          │
          ▼
      Internet ──▶ nginx ──▶ UI/API
```

**Use case**: 1–10 fires, low traffic.

---

### Option 2: Separated Pipeline + API/UI (Recommended)

```
┌──────────────────┐         ┌────────────────────┐
│  Pipeline Server │         │  API/UI Server     │
│                  │         │                    │
│  ┌────────────┐  │  rsync  │  ┌──────────────┐  │
│  │  Pipeline  │──┼────────▶│  │  data/       │  │
│  │  (cron)    │  │         │  │  products/   │  │
│  └────────────┘  │         │  └──────────────┘  │
│                  │         │                    │
│  data/           │         │  ┌──────────────┐  │
│  ├── raw/        │         │  │  API + UI    │  │
│  ├── interim/    │         │  │  (Docker)    │  │
│  └── products/   │         │  └──────────────┘  │
└──────────────────┘         └────────────────────┘
                                      │
                                      ▼
                                  Internet
```

**Use case**: 10–100 fires, moderate traffic.

**Benefits**:
- Pipeline can be resource-intensive without affecting API response times
- API/UI can be scaled horizontally (load balancer + multiple API instances)
- Clearer separation of concerns

---

### Option 3: Cloud-Native (S3 + CDN)

```
┌──────────────────┐
│  Pipeline (EC2)  │
│                  │
│  ┌────────────┐  │
│  │  Pipeline  │──┼─────┐
│  └────────────┘  │     │
└──────────────────┘     │
                         ▼
                  ┌─────────────┐
                  │  S3 Bucket  │◀───── CDN (CloudFront)
                  │  products/  │
                  └─────────────┘
                         ▲
                         │
┌──────────────────┐     │
│  API (Lambda /   │─────┘
│  ECS / K8s)      │
└──────────────────┘
         ▲
         │
┌──────────────────┐
│  UI (S3 Static   │
│  or Streamlit)   │
└──────────────────┘
```

**Use case**: 100+ fires, global audience, high availability.

**Benefits**:
- CDN for fast tile delivery worldwide
- Serverless API (Lambda) for auto-scaling
- S3 for cheap, durable storage

---

## Docker Setup

### Build Images

**Pipeline**:
```dockerfile
# Dockerfile.pipeline
FROM python:3.11-slim

WORKDIR /app

# Install GDAL and dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pipeline/ ./pipeline/
COPY configs/ ./configs/
COPY ml/ ./ml/

# Run pipeline
CMD ["python", "-m", "pipeline.run", "--config", "configs/active.yml"]
```

Build:
```bash
docker build -f Dockerfile.pipeline -t emberguide-pipeline:latest .
```

---

**API**:
```dockerfile
# Dockerfile.api
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy API code
COPY api/ ./api/

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "api.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "10"]
```

Build:
```bash
docker build -f Dockerfile.api -t emberguide-api:latest .
```

---

**UI**:
```dockerfile
# Dockerfile.ui
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy UI code
COPY ui/ ./ui/

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "ui/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false"]
```

Build:
```bash
docker build -f Dockerfile.ui -t emberguide-ui:latest .
```

---

### Docker Compose

**`docker-compose.yml`**:
```yaml
version: '3.8'

services:
  api:
    image: emberguide-api:latest
    container_name: emberguide-api
    ports:
      - "8000:8000"
    volumes:
      - ./data/products:/app/data/products:ro
    environment:
      - PRODUCTS_DIR=/app/data/products
      - LOG_LEVEL=INFO
    restart: unless-stopped

  ui:
    image: emberguide-ui:latest
    container_name: emberguide-ui
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://api:8000
    depends_on:
      - api
    restart: unless-stopped

  pipeline:
    image: emberguide-pipeline:latest
    container_name: emberguide-pipeline
    volumes:
      - ./data:/app/data
      - ./configs:/app/configs
    environment:
      - FIRMS_API_KEY=${FIRMS_API_KEY}
      - CDS_API_KEY=${CDS_API_KEY}
      - CDS_API_URL=${CDS_API_URL}
    # Run once, then exit (use cron on host)
    command: ["python", "-m", "pipeline.run", "--config", "configs/active.yml"]
```

Run:
```bash
docker-compose up -d api ui
```

---

## Environment Configuration

### `.env` File (Never Commit!)

```bash
# API Keys
FIRMS_API_KEY=your_firms_key_here
CDS_API_KEY=your_cds_key_here
CDS_API_URL=https://cds.climate.copernicus.eu/api/v2

# Paths
PRODUCTS_DIR=/app/data/products
RAW_DATA_DIR=/app/data/raw

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
CORS_ORIGINS=https://map.emberguide.example.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# ML Modules
USE_DENOISER=true
USE_CALIBRATION=true
```

Load in Docker:
```bash
docker-compose --env-file .env up -d
```

---

## Reverse Proxy (Nginx)

### Configuration

**`/etc/nginx/sites-available/emberguide`**:
```nginx
# API
server {
    listen 80;
    server_name api.emberguide.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Tiles: cache aggressively
    location /tiles/ {
        proxy_pass http://localhost:8000/tiles/;
        proxy_cache tiles_cache;
        proxy_cache_valid 200 7d;
        add_header X-Cache-Status $upstream_cache_status;
    }
}

# UI
server {
    listen 80;
    server_name map.emberguide.example.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # WebSocket support for Streamlit
        proxy_buffering off;
    }
}

# Cache zone for tiles
proxy_cache_path /var/cache/nginx/tiles levels=1:2 keys_zone=tiles_cache:10m max_size=1g inactive=7d;
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/emberguide /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### SSL/TLS (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificates
sudo certbot --nginx -d api.emberguide.example.com -d map.emberguide.example.com

# Auto-renewal (certbot installs cron job automatically)
sudo certbot renew --dry-run
```

Nginx will be auto-configured for HTTPS (port 443).

---

## Scheduled Pipeline Runs

### Cron Job

Run pipeline every 3 hours:

**`crontab -e`**:
```bash
# Run EmberGuide pipeline every 3 hours
0 */3 * * * cd /opt/emberguide && docker-compose run --rm pipeline >> /var/log/emberguide/pipeline.log 2>&1

# Cleanup old raw data (keep 30 days)
0 2 * * * find /opt/emberguide/data/raw -type f -mtime +30 -delete
```

**Alternative (systemd timer)**:

Create `/etc/systemd/system/emberguide-pipeline.service`:
```ini
[Unit]
Description=EmberGuide Pipeline
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/opt/emberguide
ExecStart=/usr/local/bin/docker-compose run --rm pipeline
User=emberguide
Group=emberguide
Environment="FIRMS_API_KEY=..."
StandardOutput=journal
StandardError=journal
```

Create `/etc/systemd/system/emberguide-pipeline.timer`:
```ini
[Unit]
Description=Run EmberGuide Pipeline every 3 hours

[Timer]
OnCalendar=*-*-* 0/3:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable emberguide-pipeline.timer
sudo systemctl start emberguide-pipeline.timer
```

---

## Monitoring & Logging

### Logging

**Structured JSON logs**:
```python
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.FileHandler("/var/log/emberguide/app.log")]
)

logger = logging.getLogger("emberguide")
logger.info(json.dumps({
    "event": "pipeline_start",
    "timestamp": datetime.utcnow().isoformat(),
    "fires_count": 5
}))
```

**Log rotation** (`/etc/logrotate.d/emberguide`):
```
/var/log/emberguide/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 emberguide emberguide
}
```

---

### Monitoring

**Health checks**:
```bash
# API health
curl https://api.emberguide.example.com/health

# Expected: {"status": "healthy", ...}
```

**Prometheus metrics** (optional):
```python
# api/main.py
from prometheus_client import Counter, Histogram, make_asgi_app

request_count = Counter("api_requests_total", "Total requests", ["endpoint", "status"])
request_duration = Histogram("api_request_duration_seconds", "Request duration", ["endpoint"])

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

**Grafana dashboard**:
- Request rate (requests/sec)
- Response time (p50, p95, p99)
- Error rate (5xx / total)
- Data freshness (time since last FIRMS update)

---

### Alerting

**Simple: Email on pipeline failure**:
```bash
# In cron
0 */3 * * * cd /opt/emberguide && docker-compose run --rm pipeline || echo "Pipeline failed" | mail -s "EmberGuide Alert" admin@example.com
```

**Advanced: PagerDuty / Slack**:
```python
import requests

def alert_on_failure(error):
    requests.post("https://hooks.slack.com/services/YOUR_WEBHOOK", json={
        "text": f"⚠️ EmberGuide pipeline failed: {error}"
    })
```

---

## Backup & Disaster Recovery

### Backup Strategy

**What to backup**:
- `data/products/` (critical; serves API/UI)
- `configs/` (version-controlled, but also backup)
- `ml/models/` (trained models)
- Database (if you add one)

**What NOT to backup**:
- `data/raw/` (can re-download)
- `data/interim/` (can regenerate)

**Backup script**:
```bash
#!/bin/bash
# /opt/emberguide/backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR=/mnt/backup/emberguide

# Backup products
rsync -av --delete /opt/emberguide/data/products/ $BACKUP_DIR/products/

# Backup configs and models
tar -czf $BACKUP_DIR/configs_models_$DATE.tar.gz \
    /opt/emberguide/configs/ \
    /opt/emberguide/ml/models/

# Keep 30 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Run daily:
```bash
# crontab
0 3 * * * /opt/emberguide/backup.sh >> /var/log/emberguide/backup.log 2>&1
```

---

### Disaster Recovery

**Scenario 1: API server crash**

1. Spin up new server
2. Restore `data/products/` from backup
3. Deploy Docker containers
4. Update DNS (if IP changed)

**Scenario 2: Pipeline server crash**

1. Spin up new server
2. Install dependencies
3. Run `make refresh` to regenerate products
4. Sync to API server

**Scenario 3: Data corruption**

1. Check backups (most recent clean backup)
2. Restore `data/products/`
3. Optionally re-run pipeline for freshest data

---

## Performance Optimization

### API

1. **Cache tiles**: Use nginx caching or CDN (CloudFront, Cloudflare)
2. **Compress responses**: Enable gzip in nginx
3. **Horizontal scaling**: Run multiple API instances behind load balancer
4. **Database for metadata**: If `index.json` gets large, use PostgreSQL + PostGIS

### Pipeline

1. **Parallel processing**: Use `multiprocessing` for independent fires
2. **Cache DEM**: SRTM tiles don't change; cache indefinitely
3. **Incremental updates**: Only fetch new FIRMS/ERA5 data
4. **Spot instances**: Use AWS Spot or GCP Preemptible for cost savings

### UI

1. **CDN for static assets**: Serve from CDN (logo, CSS)
2. **Lazy loading**: Load map tiles only when visible
3. **Debounce filters**: Don't reload on every slider change

---

## Security Best Practices

1. **Never commit secrets**: Use `.env` and `.gitignore`
2. **Firewall**: Block all ports except 80/443 (nginx)
3. **SSH key auth**: Disable password login
4. **Regular updates**: `apt update && apt upgrade` weekly
5. **Rate limiting**: Use nginx `limit_req` for API
6. **HTTPS only**: Redirect HTTP → HTTPS

**Nginx rate limiting**:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;

location /nowcast/ {
    limit_req zone=api_limit burst=10;
    proxy_pass http://localhost:8000;
}
```

---

## Cost Estimation

### AWS (example)

**Option 2 (Separated Pipeline + API/UI)**:
- Pipeline server: t3.xlarge (4 vCPU, 16 GB) — $0.1664/hr × 720h = **$120/mo**
- API/UI server: t3.medium (2 vCPU, 8 GB) — $0.0832/hr × 720h = **$60/mo**
- Storage (1 TB EBS): **$100/mo**
- Data transfer (1 TB/mo): **$90/mo**

**Total**: ~$370/mo

**Cost reduction**:
- Use Spot instances for pipeline: **-60%** → $48/mo
- Use S3 for storage: **-80%** → $23/mo
- Use CloudFront CDN for tiles: Cache hit ratio 90% → data transfer ~$10/mo

**Optimized**: ~$140/mo

---

## Troubleshooting

### "API returns 502 Bad Gateway"

**Solution**:
- Check if API container is running: `docker ps`
- Inspect logs: `docker logs emberguide-api`
- Verify nginx proxy config: `sudo nginx -t`

### "Pipeline fails with 'Out of memory'"

**Solution**:
- Increase server RAM or use swap
- Process fires sequentially instead of parallel
- Use windowed raster reads (don't load entire GeoTIFF)

### "Tiles are slow to load"

**Solution**:
- Enable nginx caching (see reverse proxy section)
- Use CDN
- Pre-generate tiles (don't generate on-demand)

---

## Next Steps

- **Data Sources**: See [docs/DATA_SOURCES.md](DATA_SOURCES.md) for API credentials setup
- **Pipeline**: See [pipeline/README.md](../pipeline/README.md) for troubleshooting pipeline errors
- **API**: See [api/README.md](../api/README.md) for endpoint details

---

## References

- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Prometheus + Grafana Tutorial](https://prometheus.io/docs/visualization/grafana/)
- [AWS Cost Calculator](https://calculator.aws/)

