# Docker Deployment Notes — Day 28

## Prerequisites

- **Docker Desktop** installed (free for personal/small business use)
- **Docker Compose** (included with Docker Desktop)
- **Ollama** running locally or accessible at `http://ollama:11434`

---

## Setup

### Step 1: Clone Secrets (Never commit real .env)

```bash
cp .env.example .env
# Edit .env and fill in your actual API keys
nano .env
```

**IMPORTANT:** Never commit `.env` to Git. It's in `.gitignore` for a reason.

### Step 2: Build and Start Stack

```bash
docker compose up --build
```

This will:
1. Build the FastAPI backend image
2. Build the Streamlit frontend image
3. Start Ollama service
4. Wire all services on a private network (`chatbot-network`)
5. Mount volumes for persistent data (coverage.db, chroma_data)

### Step 3: Verify Services Are Running

```bash
docker ps
```

Expected output:


All services should show `(healthy)` status.

---

## Access Services

| Service | URL | Purpose |
|---|---|---|
| **Backend API** | http://localhost:8000 | FastAPI endpoints |
| **Backend Health** | http://localhost:8000/health | Health check |
| **Frontend** | http://localhost:8501 | Streamlit UI |
| **Ollama** | http://localhost:11434 | LLM service |

---

## Health Checks

### Backend Health Check
The backend Dockerfile includes:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1
```

This checks every 30 seconds that the `/health` endpoint responds.

### Frontend Health Check
The frontend Dockerfile includes:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501')" || exit 1
```

### Verify Health Status

```bash
# Check all containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check specific container
docker inspect coverage-chatbot-backend | grep -A 5 '"Health"'
```

Expected output for healthy backend:



---

## Testing the Stack

### Test Backend Health Endpoint

```bash
curl http://localhost:8000/health
# Response: {"status":"ok"}
```

### Test Chat Endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "member_id": "M001",
    "message": "What is the Gold PPO premium?"
  }'
```

### Test Frontend

Open browser to http://localhost:8501 and interact with Streamlit UI.

---

## Volume Mounts Explained

In `docker-compose.yml`:

```yaml
volumes:
  - ./coverage.db:/app/coverage.db           # SQLite database (persistent)
  - ./chroma_data:/app/chroma_data           # Vector DB (persistent)
  - ./knowledge_base.jsonl:/app/knowledge_base.jsonl  # Knowledge base (persistent)
```

These mounts ensure:
- Data persists across container restarts
- Local files sync with container filesystem
- Easy backup/restore of database

---

## Environment Variables via env_file

In `docker-compose.yml`:

```yaml
services:
  backend:
    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
```

**Why `env_file` instead of hardcoding?**
- Secrets never stored in Git or Docker image
- Easy to change between environments (dev, staging, prod)
- Security best practice

---

## Stopping and Cleaning Up

### Stop all services

```bash
docker compose down
```

### Stop and remove volumes (WARNING: deletes data)

```bash
docker compose down -v
```

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

---

## Production Considerations

This docker-compose setup is suitable for **development/staging**. For production:

1. **Use Docker Registry** (Docker Hub, ECR, GCR) instead of local images
2. **Add Load Balancer** (nginx, HAProxy)
3. **Use Kubernetes** or managed container platform (ECS, GKE)
4. **Persistent volume storage** (AWS EBS, GCP Persistent Disks)
5. **Monitoring & logging** (Prometheus, DataDog, CloudWatch)
6. **Secrets management** (AWS Secrets Manager, HashiCorp Vault)
7. **Auto-scaling** based on CPU/memory usage

---

## Troubleshooting

### Backend container won't start

```bash
docker compose logs backend
```

Common issues:
- Ollama not running: `docker compose up ollama` first
- Port 8000 already in use: Change port in docker-compose.yml
- Missing .env file: `cp .env.example .env`

### Health check failing

```bash
# Check if service is actually running
docker exec coverage-chatbot-backend curl http://localhost:8000/health
```

If curl fails, Ollama or dependencies may not be ready. Wait a few seconds and retry.

### Containers exit immediately

```bash
docker compose logs backend --tail 50
```

Check for Python import errors or missing dependencies.

---

## Verification Checklist

- [ ] `docker compose up --build` completes without errors
- [ ] `docker ps` shows 3 containers (backend, frontend, ollama)
- [ ] All containers show status `(healthy)`
- [ ] `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] `curl http://localhost:8501` returns HTML (Streamlit page)
- [ ] Streamlit UI loads at http://localhost:8501
- [ ] Chat works end-to-end (question → answer)
- [ ] Logs show no errors: `docker compose logs`

---

## Conclusion

✅ The chatbot stack is now fully containerized and ready for deployment.

Next steps:
1. Push Dockerfiles and docker-compose.yml to GitHub
2. Deploy to cloud (AWS ECS, Google Cloud Run, Azure Container Instances, etc.)
3. Set up CI/CD pipeline (GitHub Actions, GitLab CI) to rebuild images on commit
4. Add monitoring and logging for production observability