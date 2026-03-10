#!/usr/bin/env python3
"""
Platform API — self-service deployment gateway for internal services.

Developers POST a deploy request here instead of running helm/kubectl directly.
The platform team controls the Helm template; teams control their own values.
"""

import subprocess
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

log = logging.getLogger("platform-api")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

app = FastAPI(
    title="Platform API",
    description="Self-service deployment gateway — deploy any service to EKS via a single POST request.",
    version="1.0.0",
)

HELM_CHART = Path(__file__).parent.parent / "helm" / "service-template"


# ── Request / Response models ──────────────────────────────────────────────────

class DeployRequest(BaseModel):
    service_name: str = Field(..., description="Unique name for the service (becomes the Helm release name)")
    image: str = Field(..., description="Full container image reference, e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/payments-api:v1.2.0")
    namespace: str = Field(default="default", description="Kubernetes namespace to deploy into")
    replicas: int = Field(default=2, ge=1, le=10, description="Number of pod replicas")
    port: int = Field(default=8080, description="Port the container listens on")
    cpu_request: str = Field(default="100m", description="CPU request (e.g. 100m, 500m)")
    memory_request: str = Field(default="128Mi", description="Memory request (e.g. 128Mi, 512Mi)")
    cpu_limit: str = Field(default="500m", description="CPU limit")
    memory_limit: str = Field(default="256Mi", description="Memory limit")
    enable_hpa: bool = Field(default=True, description="Enable Horizontal Pod Autoscaler")
    min_replicas: int = Field(default=2, ge=1, description="HPA minimum replicas")
    max_replicas: int = Field(default=10, ge=1, description="HPA maximum replicas")
    env_vars: dict[str, str] = Field(default_factory=dict, description="Environment variables to inject")


class DeployResponse(BaseModel):
    status: str
    service_name: str
    namespace: str
    image: str
    replicas: int
    message: str


class ServiceInfo(BaseModel):
    name: str
    namespace: str
    status: str
    revision: int


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/healthz", tags=["platform"])
def health():
    """Liveness probe endpoint."""
    return {"status": "ok"}


@app.post("/deploy", response_model=DeployResponse, tags=["deployments"])
def deploy(req: DeployRequest):
    """
    Deploy or update a service on EKS.

    Runs `helm upgrade --install` with the shared service-template chart.
    Idempotent — safe to call repeatedly with the same service_name.
    """
    log.info(f"Deploy request: {req.service_name} image={req.image} ns={req.namespace}")

    # Build helm set args from env_vars dict
    env_set_args = []
    for i, (k, v) in enumerate(req.env_vars.items()):
        env_set_args += [f"--set", f"env[{i}].name={k}", "--set", f"env[{i}].value={v}"]

    cmd = [
        "helm", "upgrade", "--install", req.service_name,
        str(HELM_CHART),
        "--namespace", req.namespace,
        "--create-namespace",
        "--set", f"image.repository={req.image.rsplit(':', 1)[0]}",
        "--set", f"image.tag={req.image.rsplit(':', 1)[-1] if ':' in req.image else 'latest'}",
        "--set", f"replicaCount={req.replicas}",
        "--set", f"service.port={req.port}",
        "--set", f"resources.requests.cpu={req.cpu_request}",
        "--set", f"resources.requests.memory={req.memory_request}",
        "--set", f"resources.limits.cpu={req.cpu_limit}",
        "--set", f"resources.limits.memory={req.memory_limit}",
        "--set", f"autoscaling.enabled={'true' if req.enable_hpa else 'false'}",
        "--set", f"autoscaling.minReplicas={req.min_replicas}",
        "--set", f"autoscaling.maxReplicas={req.max_replicas}",
        "--atomic",        # roll back automatically on failure
        "--timeout", "3m",
        *env_set_args,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error(f"Helm deploy failed: {result.stderr}")
        raise HTTPException(status_code=500, detail=result.stderr.strip())

    log.info(f"Deployed {req.service_name} successfully")
    return DeployResponse(
        status="deployed",
        service_name=req.service_name,
        namespace=req.namespace,
        image=req.image,
        replicas=req.replicas,
        message=result.stdout.strip(),
    )


@app.get("/services", response_model=list[ServiceInfo], tags=["deployments"])
def list_services(namespace: str = "default"):
    """List all services deployed via this platform API."""
    result = subprocess.run(
        ["helm", "list", "--namespace", namespace, "--output", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip())

    import json
    releases = json.loads(result.stdout or "[]")
    return [
        ServiceInfo(
            name=r["name"],
            namespace=r["namespace"],
            status=r["status"],
            revision=int(r["revision"]),
        )
        for r in releases
    ]


@app.delete("/services/{service_name}", tags=["deployments"])
def remove_service(service_name: str, namespace: str = "default"):
    """Remove a deployed service (helm uninstall)."""
    result = subprocess.run(
        ["helm", "uninstall", service_name, "--namespace", namespace],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=404, detail=result.stderr.strip())
    return {"status": "removed", "service_name": service_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
