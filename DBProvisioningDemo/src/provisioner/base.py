"""Abstract base class for all PostgreSQL provisioners."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProvisionResult:
    name: str
    host: str
    port: int
    db_name: str
    username: str
    version: str
    status: str = "running"
    created: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "db_name": self.db_name,
            "username": self.username,
            "version": self.version,
            "status": self.status,
            "created": self.created,
            **self.extra,
        }


class BaseProvisioner(ABC):
    """Base class for PostgreSQL provisioners."""

    def __init__(self, settings):
        self.settings = settings

    @abstractmethod
    def provision(
        self,
        name: str,
        db_name: str,
        username: str,
        password: str,
        size: str,
        version: str,
    ) -> dict:
        """Create and configure a PostgreSQL instance."""

    @abstractmethod
    def destroy(self, name: str) -> None:
        """Destroy a PostgreSQL instance."""

    @abstractmethod
    def list_instances(self) -> list[dict]:
        """Return a list of managed instances."""

    # ── Size mappings ──────────────────────────────────────────────────────────
    SIZE_MAP: dict[str, dict] = {
        "small":  {"cpu": "0.5", "memory": "512Mi", "storage": "10Gi"},
        "medium": {"cpu": "1",   "memory": "1Gi",   "storage": "50Gi"},
        "large":  {"cpu": "2",   "memory": "4Gi",   "storage": "200Gi"},
    }

    def get_size_config(self, size: str) -> dict:
        return self.SIZE_MAP.get(size, self.SIZE_MAP["small"])
