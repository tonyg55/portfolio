"""Kubernetes StatefulSet-based PostgreSQL provisioner."""
import logging
from base64 import b64encode

from .base import BaseProvisioner, ProvisionResult

log = logging.getLogger(__name__)

try:
    from kubernetes import client, config as k8s_config

    def _load_kube_config():
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

except ImportError:
    log.warning("kubernetes package not installed; K8s provisioner disabled.")
    client = None


class KubernetesProvisioner(BaseProvisioner):
    """Provisions PostgreSQL via Kubernetes StatefulSets."""

    def __init__(self, settings):
        super().__init__(settings)
        if client is None:
            raise RuntimeError("kubernetes package not installed.")
        _load_kube_config()
        self.apps = client.AppsV1Api()
        self.core = client.CoreV1Api()
        self.ns = settings.k8s_namespace
        self.storage_class = settings.k8s_storage_class
        self._ensure_namespace()

    # ── Public API ─────────────────────────────────────────────────────────────

    def provision(self, name, db_name, username, password, size, version) -> dict:
        sc = self.get_size_config(size)
        log.info(f"Provisioning K8s StatefulSet: {name} (pg{version}, {size})")

        self._create_secret(name, username, password)
        self._create_configmap(name, db_name, username)
        self._create_statefulset(name, version, sc)
        self._create_service(name)

        host = f"{name}-postgres.{self.ns}.svc.cluster.local"
        return ProvisionResult(
            name=name,
            host=host,
            port=5432,
            db_name=db_name,
            username=username,
            version=version,
            extra={"namespace": self.ns, "storage_class": self.storage_class},
        ).as_dict()

    def destroy(self, name: str) -> None:
        log.info(f"Deleting K8s resources for: {name}")
        for fn in (
            lambda: self.apps.delete_namespaced_stateful_set(f"{name}-postgres", self.ns),
            lambda: self.core.delete_namespaced_service(f"{name}-postgres", self.ns),
            lambda: self.core.delete_namespaced_config_map(f"{name}-postgres-config", self.ns),
            lambda: self.core.delete_namespaced_secret(f"{name}-postgres-secret", self.ns),
        ):
            try:
                fn()
            except Exception as e:
                log.warning(f"Delete step failed (may already be gone): {e}")

    def list_instances(self) -> list[dict]:
        sts_list = self.apps.list_namespaced_stateful_set(
            self.ns,
            label_selector="app.kubernetes.io/managed-by=pg-provision",
        )
        instances = []
        for sts in sts_list.items:
            labels = sts.metadata.labels or {}
            replicas = sts.status.ready_replicas or 0
            desired = sts.spec.replicas or 1
            status = "running" if replicas == desired else "degraded"
            name = labels.get("pg-provision/instance", sts.metadata.name)
            instances.append({
                "name": name,
                "status": status,
                "version": labels.get("pg-provision/version", "—"),
                "host": f"{name}-postgres.{self.ns}.svc.cluster.local",
                "port": 5432,
                "created": str(sts.metadata.creation_timestamp),
            })
        return instances

    # ── Private helpers ────────────────────────────────────────────────────────

    def _ensure_namespace(self):
        namespaces = [n.metadata.name for n in self.core.list_namespace().items]
        if self.ns not in namespaces:
            self.core.create_namespace(client.V1Namespace(
                metadata=client.V1ObjectMeta(name=self.ns)
            ))
            log.info(f"Created namespace: {self.ns}")

    def _create_secret(self, name: str, username: str, password: str):
        self.core.create_namespaced_secret(
            self.ns,
            client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=f"{name}-postgres-secret",
                    namespace=self.ns,
                    labels=self._labels(name),
                ),
                type="Opaque",
                data={
                    "username": b64encode(username.encode()).decode(),
                    "password": b64encode(password.encode()).decode(),
                },
            ),
        )

    def _create_configmap(self, name: str, db_name: str, username: str):
        self.core.create_namespaced_config_map(
            self.ns,
            client.V1ConfigMap(
                metadata=client.V1ObjectMeta(
                    name=f"{name}-postgres-config",
                    namespace=self.ns,
                    labels=self._labels(name),
                ),
                data={
                    "POSTGRES_DB": db_name,
                    "POSTGRES_USER": username,
                },
            ),
        )

    def _create_statefulset(self, name: str, version: str, sc: dict):
        sts = client.V1StatefulSet(
            metadata=client.V1ObjectMeta(
                name=f"{name}-postgres",
                namespace=self.ns,
                labels=self._labels(name, version),
            ),
            spec=client.V1StatefulSetSpec(
                selector=client.V1LabelSelector(
                    match_labels={"app": f"{name}-postgres"}
                ),
                service_name=f"{name}-postgres",
                replicas=1,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": f"{name}-postgres", **self._labels(name, version)}
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="postgres",
                                image=f"postgres:{version}-alpine",
                                ports=[client.V1ContainerPort(container_port=5432)],
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": sc["cpu"], "memory": sc["memory"]},
                                    limits={"cpu": sc["cpu"], "memory": sc["memory"]},
                                ),
                                env_from=[
                                    client.V1EnvFromSource(
                                        config_map_ref=client.V1ConfigMapEnvSource(
                                            name=f"{name}-postgres-config"
                                        )
                                    ),
                                ],
                                env=[
                                    client.V1EnvVar(
                                        name="POSTGRES_PASSWORD",
                                        value_from=client.V1EnvVarSource(
                                            secret_key_ref=client.V1SecretKeySelector(
                                                name=f"{name}-postgres-secret",
                                                key="password",
                                            )
                                        ),
                                    )
                                ],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name="data",
                                        mount_path="/var/lib/postgresql/data",
                                    )
                                ],
                                liveness_probe=client.V1Probe(
                                    exec=client.V1ExecAction(
                                        command=["pg_isready", "-U", "$(POSTGRES_USER)"]
                                    ),
                                    initial_delay_seconds=30,
                                    period_seconds=10,
                                ),
                                readiness_probe=client.V1Probe(
                                    exec=client.V1ExecAction(
                                        command=["pg_isready", "-U", "$(POSTGRES_USER)"]
                                    ),
                                    initial_delay_seconds=5,
                                    period_seconds=5,
                                ),
                            )
                        ]
                    ),
                ),
                volume_claim_templates=[
                    client.V1PersistentVolumeClaim(
                        metadata=client.V1ObjectMeta(name="data"),
                        spec=client.V1PersistentVolumeClaimSpec(
                            access_modes=["ReadWriteOnce"],
                            storage_class_name=self.storage_class,
                            resources=client.V1ResourceRequirements(
                                requests={"storage": sc["storage"]}
                            ),
                        ),
                    )
                ],
            ),
        )
        self.apps.create_namespaced_stateful_set(self.ns, sts)

    def _create_service(self, name: str):
        self.core.create_namespaced_service(
            self.ns,
            client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=f"{name}-postgres",
                    namespace=self.ns,
                    labels=self._labels(name),
                ),
                spec=client.V1ServiceSpec(
                    selector={"app": f"{name}-postgres"},
                    ports=[client.V1ServicePort(port=5432, target_port=5432)],
                    cluster_ip="None",  # headless service
                ),
            ),
        )

    def _labels(self, name: str, version: str = "") -> dict:
        labels = {
            "app.kubernetes.io/managed-by": "pg-provision",
            "pg-provision/instance": name,
        }
        if version:
            labels["pg-provision/version"] = version
        return labels
