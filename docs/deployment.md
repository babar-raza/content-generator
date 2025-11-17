# Deployment Guide

Complete guide for deploying UCOP to various environments.

## Deployment Options

- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Server](#production-server)
- [Cloud Deployment](#cloud-deployment)

## Local Development

### Quick Setup

```bash
# 1. Clone and setup
git clone <repo-url>
cd ucop
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your settings

# 3. Start services
# Terminal 1: Ollama (if using local models)
ollama serve

# Terminal 2: UCOP CLI
python ucop_cli.py job list

# Terminal 3: Web UI (optional)
python start_web.py
```

## Docker Deployment

### Using Docker Compose (Recommended)

```yaml
# docker-compose.yml
version: '3.8'

services:
  ucop:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./output:/app/output
      - ./config:/app/config
      - ./checkpoints:/app/checkpoints
    depends_on:
      - ollama
      - chromadb
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
  
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  ollama_data:
  chroma_data:
```

```bash
# Deploy
docker-compose up -d

# View logs
docker-compose logs -f ucop

# Stop
docker-compose down
```

### Standalone Docker

```bash
# Build image
docker build -t ucop:latest .

# Run
docker run -d \
  --name ucop \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -v $(pwd)/output:/app/output \
  ucop:latest
```

## Production Server

### System Requirements

**Hardware**:
- CPU: 8+ cores (for parallel agents)
- RAM: 16+ GB (8 GB minimum)
- Disk: 100+ GB SSD
- Network: 100+ Mbps

**Software**:
- Ubuntu 22.04 LTS (recommended)
- Python 3.10+
- Nginx (reverse proxy)
- Supervisor (process management)

### Setup Steps

#### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip nginx supervisor git

# Create app user
sudo useradd -m -s /bin/bash ucop
sudo su - ucop
```

#### 2. Application Setup

```bash
# Clone repository
cd /home/ucop
git clone <repo-url> app
cd app

# Setup virtual environment
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
vim .env  # Edit configuration

# Create directories
mkdir -p logs output data checkpoints
```

#### 3. Supervisor Configuration

```bash
# /etc/supervisor/conf.d/ucop.conf
[program:ucop-web]
command=/home/ucop/app/venv/bin/python /home/ucop/app/start_web.py
directory=/home/ucop/app
user=ucop
autostart=true
autorestart=true
stderr_logfile=/home/ucop/app/logs/web_err.log
stdout_logfile=/home/ucop/app/logs/web_out.log
environment=PATH="/home/ucop/app/venv/bin"

[program:ucop-worker]
command=/home/ucop/app/venv/bin/python /home/ucop/app/worker.py
directory=/home/ucop/app
user=ucop
numprocs=3
process_name=%(program_name)s_%(process_num)02d
autostart=true
autorestart=true
stderr_logfile=/home/ucop/app/logs/worker_%(process_num)02d_err.log
stdout_logfile=/home/ucop/app/logs/worker_%(process_num)02d_out.log
```

```bash
# Start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

#### 4. Nginx Configuration

```nginx
# /etc/nginx/sites-available/ucop
server {
    listen 80;
    server_name ucop.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    client_max_body_size 10M;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ucop /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. SSL/TLS Setup (Let's Encrypt)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d ucop.example.com

# Auto-renewal (already setup by certbot)
sudo certbot renew --dry-run
```

## Cloud Deployment

### AWS EC2

```bash
# 1. Launch EC2 instance
# - Ubuntu 22.04 LTS
# - t3.xlarge (4 vCPU, 16 GB RAM)
# - 100 GB SSD
# - Security group: HTTP (80), HTTPS (443), SSH (22)

# 2. Connect and setup
ssh -i key.pem ubuntu@<instance-ip>
sudo apt update && sudo apt upgrade -y

# 3. Follow "Production Server" steps above

# 4. Configure environment
# Use AWS Secrets Manager or Parameter Store for API keys
```

### Google Cloud Run

```bash
# 1. Create Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "start_web.py"]

# 2. Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/ucop

# 3. Deploy
gcloud run deploy ucop \
  --image gcr.io/PROJECT_ID/ucop \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key
```

### Azure Container Instances

```bash
# 1. Create container
az container create \
  --resource-group ucop-rg \
  --name ucop \
  --image ucop:latest \
  --dns-name-label ucop \
  --ports 8000 \
  --environment-variables \
    GEMINI_API_KEY=your_key
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  ucop-web:
    image: ucop:latest
    deploy:
      replicas: 3
    environment:
      - REDIS_HOST=redis
  
  ucop-worker:
    image: ucop:latest
    command: python worker.py
    deploy:
      replicas: 5
  
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
  
  redis:
    image: redis:alpine
```

### Load Balancing (Nginx)

```nginx
# nginx.conf
upstream ucop_backend {
    least_conn;
    server ucop-web-1:8000;
    server ucop-web-2:8000;
    server ucop-web-3:8000;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://ucop_backend;
    }
}
```

## Monitoring

### Health Checks

```bash
# Add health endpoint
# src/web/app.py
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Check health
curl http://localhost:8000/health
```

### Logging

```python
# config/logging.yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/ucop.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    formatter: default
  syslog:
    class: logging.handlers.SysLogHandler
    address: /dev/log
    formatter: default
root:
  level: INFO
  handlers: [file, syslog]
```

### Metrics (Prometheus)

```python
# Add metrics endpoint
from prometheus_client import Counter, Histogram, generate_latest

job_counter = Counter('ucop_jobs_total', 'Total jobs')
job_duration = Histogram('ucop_job_duration_seconds', 'Job duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# backup.sh

# Backup configuration
tar -czf /backups/config-$(date +%Y%m%d).tar.gz config/

# Backup checkpoints
tar -czf /backups/checkpoints-$(date +%Y%m%d).tar.gz checkpoints/

# Backup ChromaDB
docker exec chromadb sh -c 'tar -czf - /chroma/chroma' > /backups/chroma-$(date +%Y%m%d).tar.gz

# Cleanup old backups (>30 days)
find /backups -type f -mtime +30 -delete
```

```bash
# Add to crontab
0 2 * * * /home/ucop/app/backup.sh
```

## Security

### Firewall (UFW)

```bash
# Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### API Key Management

```bash
# Use environment variables, never commit to git
echo ".env" >> .gitignore

# Use secrets management in production
# AWS: Secrets Manager
# GCP: Secret Manager
# Azure: Key Vault
```

### Network Security

```bash
# Restrict Ollama access (if used)
# Only allow from localhost
sudo ufw deny from any to any port 11434
sudo ufw allow from 127.0.0.1 to any port 11434
```

## Troubleshooting

### Common Issues

**Port Already in Use**:
```bash
# Find process using port
sudo lsof -i :8000
# Kill process
sudo kill -9 <PID>
```

**Permission Errors**:
```bash
# Fix ownership
sudo chown -R ucop:ucop /home/ucop/app
chmod +x start_web.py
```

**Out of Memory**:
```bash
# Check memory
free -h
# Reduce max_parallel_agents in config
vim config/main.yaml
```

## Maintenance

### Updates

```bash
# 1. Backup
./backup.sh

# 2. Pull updates
git pull origin main

# 3. Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. Restart services
sudo supervisorctl restart all
```

### Log Rotation

```bash
# /etc/logrotate.d/ucop
/home/ucop/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 ucop ucop
    sharedscripts
    postrotate
        supervisorctl restart ucop-web
    endscript
}
```
