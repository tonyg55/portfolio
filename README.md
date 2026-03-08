# pg-provision — PostgreSQL Provisioning Demo

![CI](https://img.shields.io/github/actions/workflow/status/YOUR_USER/DBProvisioningDemo/ci.yml?label=CI&logo=github)
![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)
![Terraform](https://img.shields.io/badge/terraform-1.7%2B-purple?logo=terraform)
![PostgreSQL](https://img.shields.io/badge/postgresql-14%20|%2015%20|%2016-336791?logo=postgresql)
![License](https://img.shields.io/badge/license-MIT-green)

A production-quality Platform Engineering project demonstrating PostgreSQL database provisioning across three infrastructure targets: **local Docker**, **AWS RDS**, and **Kubernetes**. Built to showcase real-world platform engineering including IaC, observability, CLI tooling, and GitOps automation.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Docker Stack](#docker-stack)
- [Terraform](#terraform)
- [Kubernetes](#kubernetes)
- [Monitoring](#monitoring)
- [Architecture Decisions](#architecture-decisions)
- [Project Structure](#project-structure)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        pg-provision CLI                      │
│                         (main.py)                           │
└───────────────┬─────────────────┬───────────────────────────┘
                │                 │                 │
        ┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────────┐
        │  Local Docker│  │   AWS RDS   │  │   Kubernetes    │
        │  Provisioner │  │  Provisioner│  │   Provisioner   │
        └───────┬──────┘  └──────┬──────┘  └──────┬──────────┘
                │                │                 │
        ┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────────┐
        │ Docker Engine│  │  boto3/RDS  │  │ K8s StatefulSet │
        └──────────────┘  └─────────────┘  └─────────────────┘

Observability Stack (local):
  PostgreSQL → postgres_exporter → Prometheus → Grafana
```

The tool exposes a unified CLI interface regardless of target. Each provisioner implements the same `BaseProvisioner` abstract class, making it straightforward to add new targets (e.g., GCP Cloud SQL, Azure Database for PostgreSQL).

---

## Prerequisites

| Tool | Version | Required for |
|------|---------|-------------|
| Python | 3.11+ | CLI & provisioner logic |
| Docker Desktop | 24+ | Local target + monitoring stack |
| Terraform | 1.7+ | AWS RDS provisioning via IaC |
| kubectl | 1.28+ | Kubernetes target |
| AWS CLI | 2.x | AWS target (configured profile) |
| pg_dump / psql | 14+ | Backup & restore commands |

---

## Quick Start

### 1. Bootstrap the environment

```bash
git clone https://github.com/YOUR_USER/DBProvisioningDemo.git
cd DBProvisioningDemo
bash scripts/bootstrap.sh
source .venv/bin/activate
```

### 2. Start the local stack

```bash
make up
```

This starts PostgreSQL 16, Prometheus, Grafana, and postgres_exporter via Docker Compose.

### 3. Provision a local instance

```bash
make provision-local
# or with a custom name:
python main.py provision --target local --name mydb --db-name appdb \
  --username appuser --size medium --version 16
```

### 4. Run health checks

```bash
make health
```

### 5. Open Grafana

Navigate to http://localhost:3000 (admin / changeme) and open the **PostgreSQL Overview** dashboard.

---

## CLI Reference

All commands support `--help` for full option descriptions.

### `provision`

Create a new PostgreSQL instance on the specified target.

```bash
python main.py provision \
  --target [local|aws|k8s] \
  --name <instance-name> \
  --db-name <database> \
  --username <user> \
  --size [small|medium|large] \
  --version [14|15|16]
```

**Size classes:**

| Size | CPU | Memory | Storage |
|------|-----|--------|---------|
| small | 0.5 | 512Mi | 10Gi |
| medium | 1 | 1Gi | 50Gi |
| large | 2 | 4Gi | 200Gi |

For AWS RDS, these map to `db.t3.micro`, `db.t3.medium`, and `db.r6g.large` respectively.

### `destroy`

Destroy a provisioned instance. Prompts for confirmation unless `--force` is passed.

```bash
python main.py destroy --target local --name mydb
python main.py destroy --target aws --name mydb --force
```

### `list`

List all instances managed by pg-provision on a target.

```bash
python main.py list --target local
python main.py list --target aws
```

### `health`

Run six health checks against a PostgreSQL endpoint:

- TCP Connectivity
- Authentication
- Query Execution latency
- Inactive Replication Slots (WAL bloat risk)
- Connection utilization vs max_connections
- Autovacuum enabled

```bash
python main.py health \
  --host localhost --port 5432 \
  --db-name appdb --username appuser
```

Exits with code 1 if any check fails — suitable for use in CI pipelines and readiness gates.

### `backup`

Create a custom-format `pg_dump` backup.

```bash
python main.py backup \
  --host localhost --port 5432 \
  --db-name appdb --username appuser \
  --output backups/mydb-$(date +%Y%m%d).dump
```

---

## Docker Stack

`make up` starts four containers defined across two Compose files:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `pg-local` | postgres:16-alpine | 5432 | Primary PostgreSQL instance |
| `pg-exporter` | prometheuscommunity/postgres-exporter | 9187 | Metrics scraper |
| `pg-prometheus` | prom/prometheus | 9090 | Metrics storage & query |
| `pg-grafana` | grafana/grafana | 3000 | Dashboards |

The monitoring compose file is additive — you can run `docker compose -f docker/docker-compose.yml up -d` alone if you only want PostgreSQL.

Data is persisted in named Docker volumes (`pg_data`, `prom_data`, `grafana_data`). Run `make down` to stop and remove containers and volumes.

---

## Terraform

### Module structure

```
terraform/
├── modules/
│   ├── vpc/     # VPC, subnets, NAT gateways, RDS security group, DB subnet group
│   └── rds/     # RDS instance, parameter group, enhanced monitoring IAM role
└── environments/
    ├── dev/     # t3.micro, no Multi-AZ, local tfstate
    └── prod/    # r6g.large, Multi-AZ, S3 backend, deletion protection
```

The `rds` module provisions a production-hardened RDS instance with:
- **gp3 storage** with autoscaling
- **Storage encryption** enabled by default
- **Custom parameter group** with slow query logging, connection logging, and autovacuum tuning
- **Enhanced monitoring** via CloudWatch (configurable interval)
- **Performance Insights** (7-day retention)
- CloudWatch log export for `postgresql` and `upgrade` logs

### Deploy dev environment

```bash
cd terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set db_password via TF_VAR_db_password env var
export TF_VAR_db_password="your-secure-password"
terraform init
terraform plan
terraform apply
```

### Deploy prod environment

Update `terraform/environments/prod/main.tf` with your S3 backend bucket name, then:

```bash
cd terraform/environments/prod
export TF_VAR_db_password="$(aws secretsmanager get-secret-value ...)"
terraform init
terraform plan
terraform apply
```

---

## Kubernetes

Apply manifests in order:

```bash
kubectl apply -f kubernetes/namespace.yaml

# Edit the secret with your real password before applying
kubectl apply -f kubernetes/postgres/secret.yaml
kubectl apply -f kubernetes/postgres/configmap.yaml
kubectl apply -f kubernetes/postgres/statefulset.yaml
kubectl apply -f kubernetes/postgres/service.yaml

# Optional: monitoring
kubectl apply -f kubernetes/monitoring/postgres-exporter.yaml
kubectl apply -f kubernetes/monitoring/servicemonitor.yaml  # requires Prometheus Operator
```

Or use the Python provisioner which creates all resources programmatically:

```bash
python main.py provision --target k8s --name myapp \
  --db-name appdb --username appuser --size small --version 16
```

The ConfigMap includes a tuned `postgresql.conf` covering connection limits, WAL settings, autovacuum scale factors, and structured logging — ready to mount into the container.

---

## Monitoring

### Prometheus

Scrapes `postgres_exporter` every 15 seconds. Config: `monitoring/prometheus.yml`.

Access: http://localhost:9090

### Grafana

Dashboard: **PostgreSQL Overview** (uid: `pg-provision-overview`)

Panels included:

| Panel | Metric |
|-------|--------|
| PostgreSQL Status | `pg_up` |
| Active Connections | `pg_stat_activity_count{state="active"}` |
| Database Size | `pg_database_size_bytes` |
| Cache Hit Ratio | `blks_hit / (blks_hit + blks_read)` |
| Transaction Rate | `rate(xact_commit[5m])` + rollbacks |
| Connections by State | active / idle / idle in transaction |
| Dead Tuples | `pg_stat_user_tables_n_dead_tup` |
| Bgwriter Buffers | checkpoint / bgwriter / backend written |
| Database Size Over Time | trend line |
| Replication Lag | `pg_replication_lag` |

The dashboard JSON is importable directly from `monitoring/grafana/dashboards/postgres.json` and is also auto-provisioned when the Grafana container starts.

---

## Architecture Decisions

**Why StatefulSets for Kubernetes, not Deployments?**
StatefulSets provide stable network identities (`pod-0`, `pod-1`) and ordered pod management, which is critical for databases. Each replica gets its own PVC via `volumeClaimTemplates`, preventing data conflicts. A headless Service enables direct DNS-based pod addressing (`mydb-postgres-0.mydb-postgres.postgres.svc.cluster.local`).

**Why gp3 over gp2 for RDS storage?**
gp3 decouples IOPS and throughput from volume size, allowing you to provision exactly the performance you need without paying for larger volumes just to get more IOPS. At 20 GiB, gp3 provides 3,000 IOPS baseline vs gp2's ~100 IOPS — a significant difference for a development database.

**Why a headless Service alongside a ClusterIP Service?**
The headless service (clusterIP: None) is required by the StatefulSet controller for stable DNS. The ClusterIP service (`postgres-lb`) provides a stable virtual IP for application connections that don't need to address specific replicas — both are needed in production.

**Why custom-format (`-F c`) for pg_dump?**
Custom format supports parallel restore (`pg_restore -j`), selective table restore, and compression. It is strictly superior to plain SQL dumps for any database that will ever need to be restored quickly.

**Why pydantic-settings for configuration?**
Pydantic-settings provides type-safe, validated settings with automatic `.env` file loading and environment variable override — eliminating an entire class of runtime errors from misconfigured environments.

**Why a factory function for provisioners instead of inheritance-based dispatch?**
The `get_provisioner()` factory keeps the CLI layer thin and decoupled. Adding a new target (GCP Cloud SQL, Azure, etc.) requires only implementing `BaseProvisioner` and registering it in the factory dict — no changes to CLI commands needed.

---

## Project Structure

```
DBProvisioningDemo/
├── main.py                        # CLI entry point
├── requirements.txt
├── Makefile                       # Developer workflow automation
├── .env.example                   # All supported config variables
├── src/
│   ├── config/settings.py         # Pydantic-settings configuration
│   ├── provisioner/
│   │   ├── base.py                # Abstract base + ProvisionResult dataclass
│   │   ├── local.py               # Docker provisioner
│   │   ├── aws_rds.py             # RDS provisioner (boto3)
│   │   └── kubernetes.py          # K8s StatefulSet provisioner
│   ├── db/
│   │   ├── manager.py             # DatabaseManager (psycopg2)
│   │   └── migrations.py          # SQL migration runner
│   └── monitoring/
│       └── health.py              # Six-check health suite
├── docker/
│   ├── docker-compose.yml         # PostgreSQL service
│   └── docker-compose.monitoring.yml  # Prometheus + Grafana + exporter
├── kubernetes/
│   ├── namespace.yaml
│   ├── postgres/                  # StatefulSet, Service, ConfigMap, Secret, PVC
│   └── monitoring/                # postgres-exporter Deployment + ServiceMonitor
├── terraform/
│   ├── modules/vpc/               # VPC, subnets, NAT, security groups
│   ├── modules/rds/               # RDS instance + parameter group
│   └── environments/dev|prod/     # Environment-specific configurations
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       ├── datasources.yml
│       └── dashboards/postgres.json
├── scripts/
│   ├── bootstrap.sh               # First-time setup
│   ├── backup.sh                  # pg_dump wrapper with retention
│   └── restore.sh                 # pg_restore wrapper
└── .github/workflows/
    ├── ci.yml                     # Lint, test, docker validate, tf validate
    └── terraform-plan.yml         # PR plan comment bot
```
