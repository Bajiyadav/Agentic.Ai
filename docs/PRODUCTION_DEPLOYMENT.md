# AuditAgent Production Deployment & Operations Guide

This runbook specifies the production deployment architecture, configuration standards, operational processes, and maintenance procedures for the **AuditAgent** enterprise platform.

---

## 1. Production Architecture Overview

```mermaid
graph LR
    Internet([Public Internet / Candidates & Recruiters]) -->|Port 443 / HTTPS| Caddy[Caddy / Nginx TLS 1.3 Reverse Proxy]
    
    subgraph "Application Cluster"
        Caddy -->|Unix Socket / HTTP| Uvicorn[Gunicorn + Uvicorn Worker Pool (FastAPI)]
        Worker[Background Worker (Async AI Consensus & Batch Screening)]
    end

    subgraph "Caching & Queue"
        Uvicorn --> Redis[(Redis 7 Cluster)]
        Worker --> Redis
    end

    subgraph "Database Tier"
        Uvicorn --> PgBouncer[PgBouncer Connection Pooler]
        Worker --> PgBouncer
        PgBouncer --> PostgresPrimary[(PostgreSQL 17 Primary)]
        PostgresPrimary -.->|Streaming Replication| PostgresReplica[(PostgreSQL 17 Read Replica)]
    end
```

---

## 2. Infrastructure Prerequisites

| Component | Minimum Specification | Recommended Production Spec |
| :--- | :--- | :--- |
| **Compute (App)** | 4 vCPU, 8 GB RAM | 8 vCPU, 16 GB RAM (Scalable via K8s HPA) |
| **Database (Postgres)** | 4 vCPU, 16 GB RAM, 100 GB SSD | 8 vCPU, 32 GB RAM, 500 GB NVMe (IOPS 3000+) |
| **Cache (Redis)** | 2 vCPU, 4 GB RAM | 4 vCPU, 8 GB RAM (Redis Sentinel or AWS ElastiCache) |
| **Operating System** | Ubuntu 22.04 LTS / Debian 12 | Containerized Linux (Distroless / Alpine / Debian Slim) |

---

## 3. Containerization: Production Multi-Stage Dockerfile

Create `Dockerfile.production` at the repository root:

```dockerfile
# Stage 1: Build & Dependencies
FROM python:3.13-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Minimal Runtime
FROM python:3.13-slim AS runner

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root service account
RUN groupadd -r auditagent && useradd -r -g auditagent -d /app -s /sbin/nologin auditagent

COPY --from=builder /root/.local /home/auditagent/.local
COPY . /app

RUN chown -R auditagent:auditagent /app
USER auditagent
ENV PATH=/home/auditagent/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["gunicorn", "src.api:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
```

---

## 4. Database Configuration & PgBouncer Pooling

### PostgreSQL 17 Performance Tuning (`postgresql.conf`)
```ini
# Memory Configuration (for 16GB RAM instance)
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 32MB

# Concurrency & Connections
max_connections = 200
max_worker_processes = 8
max_parallel_workers_per_gather = 4

# Write-Ahead Logging & Durability
wal_level = replica
checkpoint_completion_target = 0.9
max_wal_size = 16GB
min_wal_size = 1GB
```

### PgBouncer Configuration (`pgbouncer.ini`)
Deploy PgBouncer directly alongside the app or database to manage persistent connection pools:
```ini
[databases]
agentic_db = host=127.0.0.1 port=5432 dbname=agentic_db auth_user=postgres

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 2000
default_pool_size = 50
reserve_pool_size = 10
reserve_pool_timeout = 5.0
```

### SQLAlchemy Connection Settings in Code (`src/db/session.py`)
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=True,  # Proactively drops stale connections
    echo=False
)
```

---

## 5. Zero-Downtime Migration Process (Alembic)

Migrations must follow the **Expand & Contract** principle:
1. **Step 1 (Expand)**: Add new nullable columns or tables via Alembic:
   ```bash
   alembic upgrade head
   ```
2. **Step 2 (Deploy Code)**: Deploy the updated application container. Code begins dual-writing or utilizing the expanded schema.
3. **Step 3 (Backfill)**: Run an asynchronous script to migrate historical rows without locking the table.
4. **Step 4 (Contract)**: Apply a follow-up migration to add NOT NULL constraints or drop deprecated columns.

---

## 6. Reverse Proxy & SSL Configuration (Caddy)

Caddy automatically obtains and renews Let's Encrypt certificates while providing HTTP/3 support:

```caddyfile
hire.yourcompany.com {
    encode gzip zstd

    # Security Headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # API and Static Routing
    reverse_proxy 127.0.0.1:8000 {
        header_up Host {upstream_hostport}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

---

## 7. Monitoring, Observability & Health Probes

### 1. Health Probe (`/api/v1/health`)
- Returns `HTTP 200` with JSON status:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",
    "cache": {
      "hits": 450,
      "misses": 50,
      "hit_rate_pct": 90.0
    }
  }
  ```
- If the database is unreachable, returns `HTTP 503 Service Unavailable`.

### 2. Prometheus Metrics (`/metrics`)
Exported metrics include:
- `http_requests_total{method, status, handler}`
- `http_request_duration_seconds_bucket`
- `candidate_evaluations_total{verdict}`
- `proctoring_violations_total{violation_type}`
- `active_db_connections`

### 3. Structured JSON Logging
All application logs are formatted in JSON for Datadog / CloudWatch / ELK consumption:
```json
{
  "timestamp": "2026-09-14T14:30:00Z",
  "level": "INFO",
  "event": "candidate_screened",
  "organization_id": "8a72b...",
  "candidate_id": "3f12a...",
  "score": 88,
  "recommendation": "STRONG_CANDIDATE",
  "duration_ms": 420
}
```

---

## 8. Backup & Disaster Recovery Runbook

1. **Daily Automated Backups**:
   - PostgreSQL WAL archiving to cloud object storage (AWS S3 / GCS) via `pgBackRest` or `wal-g`.
   - Point-in-time recovery (PITR) configured with a 30-day retention window.
2. **Weekly Cold Dump**:
   ```bash
   pg_dump -Fc -h 127.0.0.1 -U postgres agentic_db > /backup/agentic_db_$(date +%Y%m%d).dump
   ```
3. **Recovery Time Objective (RTO)**: < 15 minutes.
4. **Recovery Point Objective (RPO)**: < 1 minute (via streaming WAL replication).
