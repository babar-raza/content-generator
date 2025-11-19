# Deployment

## Overview

This guide covers deploying UCOP to production environments, including Docker containers, cloud platforms, and on-premises servers. It addresses scaling, monitoring, security, and operational best practices.

## Prerequisites

- Python 3.10+ or Docker
- 4GB+ RAM per worker
- 20GB+ disk space
- Network access to LLM providers
- (Optional) Ollama server for local inference

## Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Single Container Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p chroma_db output .jobs

# Expose ports
EXPOSE 8000 8080

# Run application
CMD ["python", "start_web.py"]
```

Build and run:

```bash
# Build image
docker build -t ucop:latest .

# Run container
docker run -d \
    --name ucop \
    -p 8000:8000 \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
    -v $(pwd)/chroma_db:/app/chroma_db \
    -v $(pwd)/output:/app/output \
    ucop:latest
```

#### Docker Compose Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ucop:
    build: .
    ports:
      - "8000:8000"
      - "8080:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    volumes:
      - ./chroma_db:/app/chroma_db
      - ./output:/app/output
      - ./config:/app/config
    depends_on:
      - ollama
    restart: unless-stopped
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - ucop
    restart: unless-stopped

volumes:
  ollama_data:
```

Run with Docker Compose:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

### Option 2: Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ucop
  labels:
    app: ucop
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ucop
  template:
    metadata:
      labels:
        app: ucop
    spec:
      containers:
      - name: ucop
        image: ucop:latest
        ports:
        - containerPort: 8000
        env:
        - name: OLLAMA_BASE_URL
          value: "http://ollama-service:11434"
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: ucop-secrets
              key: google-api-key
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        volumeMounts:
        - name: chroma-storage
          mountPath: /app/chroma_db
        - name: output-storage
          mountPath: /app/output
      volumes:
      - name: chroma-storage
        persistentVolumeClaim:
          claimName: chroma-pvc
      - name: output-storage
        persistentVolumeClaim:
          claimName: output-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ucop-service
spec:
  selector:
    app: ucop
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

Deploy to Kubernetes:

```bash
# Create namespace
kubectl create namespace ucop

# Create secrets
kubectl create secret generic ucop-secrets \
    --from-literal=google-api-key=$GOOGLE_API_KEY \
    --from-literal=openai-api-key=$OPENAI_API_KEY \
    -n ucop

# Apply manifests
kubectl apply -f k8s/ -n ucop

# Check status
kubectl get pods -n ucop

# View logs
kubectl logs -f deployment/ucop -n ucop
```

### Option 3: Native Installation

#### System Service (systemd)

Create `/etc/systemd/system/ucop.service`:

```ini
[Unit]
Description=UCOP Content Generation Platform
After=network.target

[Service]
Type=simple
User=ucop
WorkingDirectory=/opt/ucop
Environment="PATH=/opt/ucop/venv/bin"
ExecStart=/opt/ucop/venv/bin/python start_web.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
# Create user
sudo useradd -r -s /bin/false ucop

# Install application
sudo mkdir -p /opt/ucop
sudo cp -r . /opt/ucop/
sudo chown -R ucop:ucop /opt/ucop

# Create virtual environment
cd /opt/ucop
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Enable service
sudo systemctl enable ucop
sudo systemctl start ucop

# Check status
sudo systemctl status ucop

# View logs
sudo journalctl -u ucop -f
```

## Production Configuration

### Environment Variables

Create `.env.production`:

```bash
# LLM Providers
OLLAMA_BASE_URL=http://ollama:11434
GOOGLE_API_KEY=<production_key>
OPENAI_API_KEY=<production_key>

# GitHub
GITHUB_TOKEN=<production_token>

# Paths
CHROMA_DB_PATH=/data/chroma_db
OUTPUT_PATH=/data/output

# Performance
MAX_WORKERS=5
WORKER_MEMORY_GB=4

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/ucop/ucop.log

# Security
ALLOWED_HOSTS=ucop.example.com
CORS_ORIGINS=https://ucop.example.com
API_KEY_REQUIRED=true
```

### Production Settings

Create `config/production.yaml`:

```yaml
# Production configuration
environment: production

# High-performance settings
workflows:
  use_langgraph: true
  enable_parallel_execution: true
  max_parallel_agents: 10

jobs:
  max_concurrent_jobs: 10
  max_retries: 3
  retry_delay_seconds: 60

# Resource limits
agents:
  default_resources:
    max_memory_mb: 4096
    max_runtime_s: 900
    max_tokens: 16384

# Monitoring
monitoring:
  enabled: true
  metrics_port: 9090
  health_check_interval: 60

# Logging
logging:
  level: INFO
  format: json
  file: /var/log/ucop/ucop.log
  max_size_mb: 100
  backup_count: 10

# Security
security:
  api_key_required: true
  rate_limiting: true
  max_requests_per_minute: 60
```

## Scaling Strategies

### Horizontal Scaling

#### Multi-Worker Setup

Create `docker-compose.scale.yml`:

```yaml
version: '3.8'

services:
  ucop-worker:
    build: .
    deploy:
      replicas: 5
    environment:
      - WORKER_ID=${HOSTNAME}
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - shared-chroma:/app/chroma_db
      - shared-output:/app/output
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - ucop-worker

volumes:
  shared-chroma:
  shared-output:
```

Scale workers:

```bash
# Scale to 10 workers
docker-compose -f docker-compose.scale.yml up -d --scale ucop-worker=10

# Scale down to 3 workers
docker-compose -f docker-compose.scale.yml up -d --scale ucop-worker=3
```

#### Load Balancer Configuration

Create `nginx-lb.conf`:

```nginx
upstream ucop_backend {
    least_conn;
    server ucop-worker-1:8000 max_fails=3 fail_timeout=30s;
    server ucop-worker-2:8000 max_fails=3 fail_timeout=30s;
    server ucop-worker-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name ucop.example.com;
    
    location / {
        proxy_pass http://ucop_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /health {
        proxy_pass http://ucop_backend/health;
        access_log off;
    }
}
```

### Vertical Scaling

Increase resources per worker:

```yaml
# docker-compose.yml
services:
  ucop:
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
        reservations:
          cpus: '4'
          memory: 8G
```

## Database and Storage

### Persistent Storage

#### ChromaDB Persistence

```bash
# Create persistent volume
docker volume create chroma_data

# Mount in container
docker run -v chroma_data:/app/chroma_db ucop:latest
```

#### Output Storage

Options for output storage:
- Local filesystem (development)
- Network filesystem (NFS, CIFS)
- Object storage (S3, MinIO, Azure Blob)
- Database (PostgreSQL for metadata)

Example S3 integration:

```python
# config/storage.yaml
storage:
  backend: s3
  s3:
    bucket: ucop-output
    region: us-east-1
    access_key: ${AWS_ACCESS_KEY}
    secret_key: ${AWS_SECRET_KEY}
```

## Monitoring and Health Checks

### Health Check Endpoint

```python
# start_web.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.0"
    }
```

Docker health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

Kubernetes readiness probe:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Metrics Collection

Prometheus configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ucop'
    static_configs:
      - targets: ['ucop:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Security Hardening

### SSL/TLS Configuration

#### Nginx SSL

```nginx
server {
    listen 443 ssl http2;
    server_name ucop.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://ucop_backend;
    }
}
```

#### Let's Encrypt

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d ucop.example.com

# Auto-renewal
certbot renew --dry-run
```

### API Key Management

```python
# Require API key for all requests
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    if not verify_key(api_key):
        return JSONResponse({"error": "Invalid API key"}, 401)
    return await call_next(request)
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/generate")
@limiter.limit("10/minute")
async def generate(request: Request):
    # Implementation
    pass
```

## Backup and Recovery

### Backup Strategy

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups

# Backup ChromaDB
tar -czf $BACKUP_DIR/chroma_$DATE.tar.gz chroma_db/

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/

# Backup job data
tar -czf $BACKUP_DIR/jobs_$DATE.tar.gz .jobs/

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

Schedule backups:

```bash
# Add to crontab
0 2 * * * /opt/ucop/backup.sh
```

### Disaster Recovery

```bash
# Restore from backup
cd /opt/ucop

# Stop service
systemctl stop ucop

# Restore data
tar -xzf /backups/chroma_20241117.tar.gz
tar -xzf /backups/config_20241117.tar.gz
tar -xzf /backups/jobs_20241117.tar.gz

# Start service
systemctl start ucop
```

## Maintenance

### Update Procedure

```bash
# 1. Backup current installation
./backup.sh

# 2. Pull updates
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt --upgrade

# 4. Run migrations (if any)
python tools/migrate.py

# 5. Restart service
systemctl restart ucop

# 6. Verify deployment
python tools/validate_production.py
```

### Log Rotation

```bash
# /etc/logrotate.d/ucop
/var/log/ucop/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ucop ucop
    postrotate
        systemctl reload ucop
    endscript
}
```

## Troubleshooting

### Common Issues

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Reduce parallel execution
# Edit config/main.yaml:
max_parallel_agents: 3

# Restart service
docker-compose restart
```

#### Slow Performance

```bash
# Check agent metrics
python ucop_cli.py viz bottlenecks

# Increase workers
docker-compose up -d --scale ucop-worker=10

# Enable caching
# Edit config/main.yaml:
caching:
  enabled: true
```

#### Connection Errors

```bash
# Check network connectivity
curl http://ollama:11434/api/tags

# Check DNS resolution
nslookup ollama

# Check firewall
iptables -L
```

## Best Practices

1. **Use Docker**: Containerization simplifies deployment
2. **Enable monitoring**: Track metrics and logs
3. **Implement backups**: Regular automated backups
4. **Use SSL/TLS**: Encrypt all network traffic
5. **Rate limiting**: Prevent API abuse
6. **Health checks**: Monitor service availability
7. **Auto-scaling**: Scale based on demand
8. **Regular updates**: Keep dependencies current
9. **Test deployments**: Validate before production
10. **Document changes**: Track configuration changes

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
