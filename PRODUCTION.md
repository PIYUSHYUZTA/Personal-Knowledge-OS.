# PKOS Production Deployment Guide

This guide covers deploying the Personal Knowledge OS (PKOS) to production.

## System Requirements

- Docker & Docker Compose (v1.29+)
- 4GB+ RAM
- 20GB+ storage (for databases and uploads)
- Linux-based server (Ubuntu 20.04+ recommended)

## Pre-Deployment Setup

### 1. Clone and Prepare the Repository

```bash
git clone <repo-url> pkos
cd pkos
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your production values
nano .env
```

**Critical variables that MUST be set:**

```bash
# LLM API Keys (required - set at least one)
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...

# Security
JWT_SECRET_KEY=your-long-random-secure-key-min-32-chars
POSTGRES_PASSWORD=strong-password-change-me
NEO4J_PASSWORD=strong-password-change-me
REDIS_PASSWORD=strong-password-change-me

# Frontend Configuration
VITE_API_URL=https://your-domain.com  # Use HTTPS in production
APP_PORT=3000
```

### 3. Create Required Directories

```bash
mkdir -p data/{postgres,neo4j/{data,logs},redis,uploads,knowledge_base,nginx_cache}
chmod -R 755 data
```

### 4. Generate Secure JWT Secret (if not using a pre-generated one)

```bash
openssl rand -hex 32
# Copy output to JWT_SECRET_KEY in .env
```

## Deployment Options

### Option A: Docker Compose (Recommended for Single-Server)

#### Start Services

```bash
# Pull and build images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Verify services are healthy
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### Database Initialization

After the first startup, initialize the database:

```bash
# Run migrations (if using Alembic)
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Seed initial data (optional)
docker-compose -f docker-compose.prod.yml exec backend python scripts/seed_db.py
```

#### Verify Deployment

```bash
# Test API health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000

# Check Neo4j
curl -u neo4j:$NEO4J_PASSWORD http://localhost:7474/browser/
```

### Option B: Kubernetes Deployment

For high-availability deployments, use Kubernetes:

```bash
# Create namespace
kubectl create namespace pkos

# Create secrets
kubectl create secret generic pkos-secrets \
  --from-env-file=.env \
  -n pkos

# Deploy
kubectl apply -f k8s/
```

## Configuration Details

### Multi-Model LLM Factory

PKOS uses a multi-model LLM factory with automatic fallback:

**Primary (if available):**
- Claude 3.5 Sonnet

**Fallback chain:**
- GPT-4o
- Gemini 1.5 Pro

**Validation (lightweight):**
- Claude Haiku (code validation only)

To use a different primary model, set in `.env`:

```bash
# Edit backend environment before starting
LLM_PRIMARY_PROVIDER=gpt4  # Options: claude, gpt4, gemini
```

### Caching Strategy

Redis caching is enabled by default with:

- Query result TTL: 1-2 hours
- Semantic search cache: 2 hours
- Graph query cache: 1 hour

Disable caching if needed:

```bash
REDIS_ENABLED=false
```

### PostgreSQL Optimization

PostgreSQL starts with default settings. For large datasets, optimize:

```bash
# After starting, connect and optimize
docker-compose -f docker-compose.prod.yml exec postgres psql -U pkos_user -d pkos

# Example optimizations
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
SELECT pg_reload_conf();
```

### Neo4j Performance

Neo4j is configured with:

- Heap: 1GB
- Page Cache: 512MB
- APOC plugins enabled

For larger graphs:

```bash
# Update in docker-compose.prod.yml
NEO4J_dbms_memory_heap_max__size: 2G
NEO4J_dbms_memory_pagecache_size: 1G
```

## Monitoring & Maintenance

### Health Checks

All services have built-in health checks. Monitor with:

```bash
# Docker Compose
docker-compose -f docker-compose.prod.yml ps

# Individual service logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f postgres
```

### Backup Strategy

#### PostgreSQL Backup

```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
  -U pkos_user -d pkos > backup-$(date +%Y%m%d).sql

# Automated daily backups (add to crontab)
0 2 * * * cd /path/to/pkos && docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U pkos_user -d pkos > backups/backup-$(date +\%Y\%m\%d).sql
```

#### Neo4j Backup

```bash
# Neo4j backup (requires enterprise edition or paid feature)
docker-compose -f docker-compose.prod.yml exec neo4j \
  neo4j-admin dump --to-path=/var/lib/neo4j/data/backups
```

#### Volume Backups

```bash
# Backup persistent volumes
docker run --rm -v pkos_postgres_data:/data -v $(pwd)/backups:/backups \
  alpine tar czf /backups/postgres-data.tar.gz -C /data .
```

### Monitoring Metrics

#### LLM Usage & Costs

View usage statistics at:

```bash
# API endpoint
curl http://localhost:8000/api/stats/llm-usage

# Expected response
{
  "claude": {
    "total_tokens": 125000,
    "total_cost": "$3.75",
    "model_id": "claude-3-5-sonnet-20241022"
  },
  "gpt4": {
    "total_tokens": 45000,
    "total_cost": "$2.25",
    "model_id": "gpt-4o"
  }
}
```

#### Database Metrics

```bash
# PostgreSQL info
docker-compose -f docker-compose.prod.yml exec postgres psql \
  -U pkos_user -d pkos -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datname = 'pkos';"

# Neo4j info
curl -X GET http://localhost:7474/db/neo4j/metrics \
  -u neo4j:$NEO4J_PASSWORD
```

## Security Hardening

### 1. Update Default Credentials

```bash
# Change all default passwords in .env
# Change PostgreSQL password
# Change Neo4j password
# Change Redis password
```

### 2. Enable HTTPS

Update `docker-compose.prod.yml`:

```yaml
environment:
  # Add to backend
  CORS_ORIGINS: ['https://your-domain.com']

  # Add to frontend
  VITE_API_URL: https://your-domain.com/api
```

Use Let's Encrypt with Nginx:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Update nginx SSL configuration
```

### 3. Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432       # PostgreSQL (only internal)
sudo ufw deny 7687       # Neo4j (only internal)
sudo ufw deny 6379       # Redis (only internal)
```

### 4. Database Connection Security

- PostgreSQL uses pgvector image with SSL support
- Neo4j uses encrypted connections (BOLT protocol)
- Redis can use AUTH with strong passwords

## Troubleshooting

### Services Not Starting

```bash
# Check logs for all services
docker-compose -f docker-compose.prod.yml logs

# Check specific service
docker-compose -f docker-compose.prod.yml logs backend

# Check Docker resources
docker stats
```

### Database Connection Errors

```bash
# Verify PostgreSQL is healthy
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U pkos_user

# Check connection string
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE_URL
```

### LLM API Failures

```bash
# Verify API keys are set
docker-compose -f docker-compose.prod.yml exec backend env | grep API_KEY

# Check which provider is active
curl http://localhost:8000/api/stats/providers
```

### WebSocket Connection Issues

```bash
# Check if WebSocket is reachable
wscat -c ws://localhost:8000/api/v1/stream/query?token=YOUR_TOKEN

# Check Nginx WebSocket forwarding
# Ensure proxy_upgrade directive is set in nginx.conf
```

## Scaling

### Horizontal Scaling

To run multiple backend instances:

```yaml
# docker-compose.prod.yml
backend:
  deploy:
    replicas: 3  # Run 3 backend instances
```

### Vertical Scaling

Increase resource limits in `docker-compose.prod.yml`:

```yaml
resources:
  limits:
    cpus: '4'
    memory: 4G
  reservations:
    cpus: '2'
    memory: 2G
```

## Updating PKOS

```bash
# Pull latest changes
git pull origin main

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

## Support & Documentation

- **Issues**: GitHub Issues
- **Documentation**: `/docs`
- **API Docs**: `http://your-domain.com/api/docs`

For production support, consider:
- Setting up monitoring (Prometheus + Grafana)
- Configuring log aggregation (ELK stack)
- Setting up alerting (PagerDuty, Datadog)
