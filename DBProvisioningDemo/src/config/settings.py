"""Application settings loaded from environment / .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Local
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)

    # AWS
    aws_region: str = Field(default="us-east-1")
    aws_profile: str = Field(default="default")
    rds_subnet_group: str = Field(default="")
    rds_security_group_id: str = Field(default="")
    rds_parameter_group: str = Field(default="default.postgres16")
    rds_backup_retention_days: int = Field(default=7)
    rds_multi_az: bool = Field(default=False)
    rds_deletion_protection: bool = Field(default=False)

    # Kubernetes
    kubeconfig: str = Field(default="~/.kube/config")
    k8s_namespace: str = Field(default="postgres")
    k8s_storage_class: str = Field(default="standard")

    # Monitoring
    grafana_admin_password: str = Field(default="changeme")
