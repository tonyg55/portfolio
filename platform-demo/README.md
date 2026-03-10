# platform-demo — Internal Platform Engineering Demo

This project demonstrates a Platform Engineering pattern where developers self-service deploy services to EKS via a platform API, instead of managing Kubernetes directly. The platform team owns the infrastructure (Terraform) and the deployment template (Helm chart); developers own their service code.

## Architecture

```
Developer
    │  POST /deploy {image, replicas, port}
    ▼
Platform API (FastAPI)
    │  helm upgrade --install
    ▼
Helm service-template chart
    │
    ▼
EKS Cluster (provisioned by Terraform)
    └── Deployment + Service + HPA
```

## Components

| Component | Purpose |
|-----------|---------|
| `terraform/` | Provisions EKS cluster, managed node group, ECR repo, and IAM roles (including OIDC role for GitHub Actions) |
| `platform-api/` | FastAPI service exposing `/deploy`, `/services`, and `/healthz` — wraps `helm upgrade --install` |
| `helm/service-template/` | Shared Helm chart rendered at deploy time; includes Deployment, Service, and HPA |
| `.github/workflows/` | CI/CD pipeline: builds image, pushes to ECR, deploys via Helm on push to `main` |

## Local Dev

```bash
cd platform-api
pip install -r requirements.txt
uvicorn main:app --reload
# API docs at http://localhost:8000/docs
```

## Deploying to AWS

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Push to `main` to trigger GitHub Actions, which builds the image, pushes to ECR, and deploys via Helm.

## Example API Calls

```bash
# Deploy a service
curl -X POST http://localhost:8000/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "payments-api",
    "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/payments-api:v1.2.0",
    "namespace": "production",
    "replicas": 3,
    "port": 8080,
    "env_vars": {"DATABASE_URL": "postgres://..."}
  }'

# List deployed services
curl http://localhost:8000/services?namespace=production

# Remove a service
curl -X DELETE http://localhost:8000/services/payments-api?namespace=production
```

## GitHub Actions Setup

One secret required in your GitHub repo settings:

| Secret | Value |
|--------|-------|
| `AWS_ROLE_ARN` | Output of `terraform output github_actions_role_arn` |

Also update `YOUR_GITHUB_ORG` in `terraform/iam.tf` before applying.

## Design Decisions

- **OIDC instead of access keys** — GitHub Actions assumes an IAM role via short-lived OIDC tokens. No long-lived credentials stored as secrets, no rotation required.
- **`--atomic` on helm deploy** — If any pod fails to become ready within the timeout, Helm automatically rolls back to the previous release. Failures are never silently left in a broken state.
- **HPA on by default** — Services scale horizontally under load without manual intervention. The `replicas` field in the deploy request sets the baseline; HPA takes over from there.
