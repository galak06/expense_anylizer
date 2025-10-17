# Docker Deployment Guide

## 🐳 Running Expense Analyzer with Docker

This guide explains how to run the Expense Analyzer application using Docker.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed (usually comes with Docker Desktop)

---

## Quick Start

### Option 1: Using Docker Compose (Recommended)

The easiest way to run the application:

```bash
# Start the application
docker-compose up

# Or run in detached mode (background)
docker-compose up -d
```

The application will be available at: **http://localhost:8501**

To stop the application:
```bash
docker-compose down
```

### Option 2: Using Docker directly

```bash
# Build the Docker image
docker build -t expense-analyzer .

# Run the container
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  --name expense-analyzer \
  expense-analyzer
```

---

## Configuration

### Environment Variables

You can configure the application using environment variables:

**In `docker-compose.yml`:**
```yaml
environment:
  - OPENAI_API_KEY=your_api_key_here  # For AI categorization
  - STREAMLIT_SERVER_PORT=8501
```

**Or using `.env` file:**
```bash
# Create .env file
cp .env.example .env

# Edit with your values
nano .env
```

Then Docker Compose will automatically load the variables.

### Data Persistence

The `data/` directory is mounted as a volume to persist:
- Database (`transactions.db`)
- Profiles (`profiles.yaml`)
- Uploaded files

**Volume Configuration:**
```yaml
volumes:
  - ./data:/app/data
```

---

## Docker Commands

### Build and Run
```bash
# Build the image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Container Management
```bash
# List running containers
docker ps

# View container logs
docker logs expense-analyzer

# Execute commands in container
docker exec -it expense-analyzer bash

# Restart container
docker restart expense-analyzer

# Stop container
docker stop expense-analyzer

# Remove container
docker rm expense-analyzer
```

### Image Management
```bash
# List images
docker images

# Remove image
docker rmi expense-analyzer

# Prune unused images
docker image prune
```

---

## Health Check

The Docker container includes a health check that monitors the application:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' expense-analyzer

# View health check logs
docker inspect expense-analyzer | grep -A 20 Health
```

**Health check details:**
- Interval: 30 seconds
- Timeout: 10 seconds
- Start period: 40 seconds
- Retries: 3

---

## Networking

The application runs on port **8501** by default.

**To change the port:**

Edit `docker-compose.yml`:
```yaml
ports:
  - "3000:8501"  # Access on port 3000 instead
```

Or with Docker run:
```bash
docker run -p 3000:8501 expense-analyzer
```

---

## Troubleshooting

### Container won't start

**Check logs:**
```bash
docker-compose logs expense-analyzer
```

**Common issues:**
- Port 8501 already in use → Change port mapping
- Permission issues → Check data directory permissions
- Missing dependencies → Rebuild image

### Application not accessible

**Verify container is running:**
```bash
docker ps | grep expense-analyzer
```

**Check port mapping:**
```bash
docker port expense-analyzer
```

**Test health endpoint:**
```bash
curl http://localhost:8501/_stcore/health
```

### Data not persisting

**Verify volume mount:**
```bash
docker inspect expense-analyzer | grep -A 10 Mounts
```

**Check data directory permissions:**
```bash
ls -la data/
```

### Rebuild after code changes

```bash
# Stop and remove existing container
docker-compose down

# Rebuild and start
docker-compose up -d --build
```

---

## Production Deployment

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml expense-analyzer

# List services
docker service ls

# View service logs
docker service logs expense-analyzer_expense-analyzer
```

### Using Kubernetes

Create `deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: expense-analyzer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: expense-analyzer
  template:
    metadata:
      labels:
        app: expense-analyzer
    spec:
      containers:
      - name: expense-analyzer
        image: expense-analyzer:latest
        ports:
        - containerPort: 8501
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: expense-analyzer-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: expense-analyzer
spec:
  selector:
    app: expense-analyzer
  ports:
  - port: 80
    targetPort: 8501
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f deployment.yaml
```

---

## Advanced Configuration

### Custom Streamlit Config

Create `.streamlit/config.toml` in your project:
```toml
[server]
port = 8501
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

Then update Dockerfile to copy it:
```dockerfile
COPY .streamlit/config.toml /app/.streamlit/config.toml
```

### Multi-Container Setup

If you want to add additional services (e.g., PostgreSQL, Redis):

```yaml
version: '3.8'

services:
  expense-analyzer:
    build: .
    depends_on:
      - postgres
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/expenses

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=expenses
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
```

---

## Security Best Practices

1. **Use environment variables for secrets**
   ```bash
   # Never commit .env files
   echo ".env" >> .gitignore
   ```

2. **Run as non-root user**
   Add to Dockerfile:
   ```dockerfile
   RUN useradd -m -u 1000 appuser
   USER appuser
   ```

3. **Scan images for vulnerabilities**
   ```bash
   docker scan expense-analyzer
   ```

4. **Use specific base image versions**
   ```dockerfile
   FROM python:3.11.5-slim
   ```

5. **Limit container resources**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1'
         memory: 1G
   ```

---

## Monitoring

### Container Stats
```bash
# Real-time stats
docker stats expense-analyzer

# Memory usage
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}"
```

### Application Logs
```bash
# Follow logs
docker-compose logs -f expense-analyzer

# Last 100 lines
docker-compose logs --tail=100 expense-analyzer

# Filter by time
docker-compose logs --since 10m expense-analyzer
```

---

## Backup and Restore

### Backup Data
```bash
# Backup database
docker exec expense-analyzer tar czf - /app/data | cat > backup-$(date +%Y%m%d).tar.gz

# Or use volume backup
docker run --rm -v expense_analyzer_data:/data -v $(pwd):/backup ubuntu tar czf /backup/data-backup.tar.gz /data
```

### Restore Data
```bash
# Restore database
cat backup-20251012.tar.gz | docker exec -i expense-analyzer tar xzf - -C /

# Or restore volume
docker run --rm -v expense_analyzer_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/data-backup.tar.gz -C /
```

---

## Performance Tuning

### Optimize Image Size
```dockerfile
# Use slim base image
FROM python:3.11-slim

# Multi-stage build
FROM python:3.11 as builder
# ... build steps
FROM python:3.11-slim
COPY --from=builder /app /app
```

### Cache Dependencies
```dockerfile
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

---

## Support

If you encounter issues:
1. Check logs: `docker-compose logs`
2. Verify configuration: `docker-compose config`
3. Test health: `curl http://localhost:8501/_stcore/health`
4. Review [Streamlit Docker docs](https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker)

---

## Summary

**Start application:**
```bash
docker-compose up -d
```

**Stop application:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f
```

**Access application:**
```
http://localhost:8501
```

🎉 Your Expense Analyzer is now running in Docker!
