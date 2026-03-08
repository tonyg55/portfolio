"""Local Docker-based PostgreSQL provisioner."""
import json
import logging
import subprocess
from datetime import datetime

from .base import BaseProvisioner, ProvisionResult

log = logging.getLogger(__name__)

STATE_LABEL = "pg-provision.managed"
VERSION_LABEL = "pg-provision.version"
DB_LABEL = "pg-provision.db"
USER_LABEL = "pg-provision.user"


class LocalProvisioner(BaseProvisioner):
    """Provisions PostgreSQL instances as Docker containers."""

    def provision(self, name, db_name, username, password, size, version) -> dict:
        container_name = f"pg-{name}"
        log.info(f"Provisioning local container: {container_name} (pg{version})")

        # Check if already exists
        if self._container_exists(container_name):
            raise RuntimeError(f"Container '{container_name}' already exists.")

        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-e", f"POSTGRES_DB={db_name}",
            "-e", f"POSTGRES_USER={username}",
            "-e", f"POSTGRES_PASSWORD={password}",
            "-p", "0:5432",  # random host port
            "-l", f"{STATE_LABEL}=true",
            "-l", f"{VERSION_LABEL}={version}",
            "-l", f"{DB_LABEL}={db_name}",
            "-l", f"{USER_LABEL}={username}",
            "--health-cmd", "pg_isready -U $POSTGRES_USER",
            "--health-interval", "10s",
            "--health-retries", "5",
            f"postgres:{version}-alpine",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"docker run failed: {result.stderr.strip()}")

        host_port = self._get_host_port(container_name)
        log.info(f"Container started on host port {host_port}")

        return ProvisionResult(
            name=name,
            host="localhost",
            port=host_port,
            db_name=db_name,
            username=username,
            version=version,
            extra={"container": container_name},
        ).as_dict()

    def destroy(self, name: str) -> None:
        container_name = f"pg-{name}"
        log.info(f"Destroying container: {container_name}")
        for action in ("stop", "rm"):
            result = subprocess.run(
                ["docker", action, container_name],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"docker {action} {container_name} failed: {result.stderr.strip()}"
                )

    def list_instances(self) -> list[dict]:
        result = subprocess.run(
            [
                "docker", "ps", "-a",
                "--filter", f"label={STATE_LABEL}=true",
                "--format", "{{json .}}",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"docker ps failed: {result.stderr.strip()}")

        instances = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            data = json.loads(line)
            labels = self._parse_labels(data.get("Labels", ""))
            name = data.get("Names", "").lstrip("/").removeprefix("pg-")
            status = "running" if "Up" in data.get("Status", "") else "stopped"
            port = self._extract_port(data.get("Ports", ""))
            instances.append({
                "name": name,
                "status": status,
                "version": labels.get(VERSION_LABEL, "—"),
                "host": "localhost",
                "port": port,
                "created": data.get("CreatedAt", "—"),
            })
        return instances

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _container_exists(self, name: str) -> bool:
        result = subprocess.run(
            ["docker", "ps", "-a", "-q", "--filter", f"name=^/{name}$"],
            capture_output=True, text=True,
        )
        return bool(result.stdout.strip())

    def _get_host_port(self, container_name: str) -> int:
        result = subprocess.run(
            ["docker", "inspect", "--format",
             "{{(index (index .NetworkSettings.Ports \"5432/tcp\") 0).HostPort}}",
             container_name],
            capture_output=True, text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return 5432
        return int(result.stdout.strip())

    @staticmethod
    def _parse_labels(labels_str: str) -> dict:
        labels = {}
        for part in labels_str.split(","):
            if "=" in part:
                k, _, v = part.partition("=")
                labels[k.strip()] = v.strip()
        return labels

    @staticmethod
    def _extract_port(ports_str: str) -> str:
        """Extract mapped host port from docker ps Ports column."""
        # e.g. "0.0.0.0:32768->5432/tcp"
        for part in ports_str.split(","):
            part = part.strip()
            if "->5432" in part:
                return part.split(":")[1].split("->")[0]
        return "—"
