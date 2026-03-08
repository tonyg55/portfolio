"""AWS RDS PostgreSQL provisioner using boto3."""
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from .base import BaseProvisioner, ProvisionResult

log = logging.getLogger(__name__)

# Maps size class → RDS instance class
RDS_INSTANCE_CLASS = {
    "small":  "db.t3.micro",
    "medium": "db.t3.medium",
    "large":  "db.r6g.large",
}

# Maps size class → allocated storage (GiB)
RDS_STORAGE = {
    "small":  20,
    "medium": 100,
    "large":  500,
}


class AWSRDSProvisioner(BaseProvisioner):
    """Provisions PostgreSQL instances on AWS RDS."""

    def __init__(self, settings):
        super().__init__(settings)
        session = boto3.Session(
            region_name=settings.aws_region,
            profile_name=settings.aws_profile,
        )
        self.rds = session.client("rds")

    def provision(self, name, db_name, username, password, size, version) -> dict:
        identifier = f"pg-provision-{name}"
        log.info(f"Creating RDS instance: {identifier}")

        kwargs: dict[str, Any] = {
            "DBInstanceIdentifier": identifier,
            "DBName": db_name,
            "MasterUsername": username,
            "MasterUserPassword": password,
            "DBInstanceClass": RDS_INSTANCE_CLASS[size],
            "Engine": "postgres",
            "EngineVersion": f"{version}.0",
            "AllocatedStorage": RDS_STORAGE[size],
            "StorageType": "gp3",
            "StorageEncrypted": True,
            "MultiAZ": self.settings.rds_multi_az,
            "BackupRetentionPeriod": self.settings.rds_backup_retention_days,
            "DeletionProtection": self.settings.rds_deletion_protection,
            "Tags": [
                {"Key": "managed-by", "Value": "pg-provision"},
                {"Key": "instance-name", "Value": name},
                {"Key": "environment", "Value": "portfolio"},
            ],
        }

        if self.settings.rds_subnet_group:
            kwargs["DBSubnetGroupName"] = self.settings.rds_subnet_group
        if self.settings.rds_security_group_id:
            kwargs["VpcSecurityGroupIds"] = [self.settings.rds_security_group_id]
        if self.settings.rds_parameter_group:
            kwargs["DBParameterGroupName"] = self.settings.rds_parameter_group

        try:
            resp = self.rds.create_db_instance(**kwargs)
        except ClientError as e:
            raise RuntimeError(f"RDS CreateDBInstance failed: {e}") from e

        log.info(f"Waiting for {identifier} to become available (this may take several minutes)...")
        waiter = self.rds.get_waiter("db_instance_available")
        waiter.wait(DBInstanceIdentifier=identifier,
                    WaiterConfig={"Delay": 30, "MaxAttempts": 40})

        # Refresh to get endpoint
        desc = self.rds.describe_db_instances(DBInstanceIdentifier=identifier)
        db = desc["DBInstances"][0]
        endpoint = db["Endpoint"]

        return ProvisionResult(
            name=name,
            host=endpoint["Address"],
            port=endpoint["Port"],
            db_name=db_name,
            username=username,
            version=db["EngineVersion"],
            extra={
                "identifier": identifier,
                "arn": db["DBInstanceArn"],
                "instance_class": db["DBInstanceClass"],
                "storage_encrypted": db["StorageEncrypted"],
            },
        ).as_dict()

    def destroy(self, name: str) -> None:
        identifier = f"pg-provision-{name}"
        log.info(f"Deleting RDS instance: {identifier}")
        try:
            self.rds.delete_db_instance(
                DBInstanceIdentifier=identifier,
                SkipFinalSnapshot=True,
                DeleteAutomatedBackups=False,
            )
        except ClientError as e:
            raise RuntimeError(f"RDS DeleteDBInstance failed: {e}") from e

        log.info("Waiting for deletion to complete...")
        waiter = self.rds.get_waiter("db_instance_deleted")
        waiter.wait(DBInstanceIdentifier=identifier,
                    WaiterConfig={"Delay": 30, "MaxAttempts": 60})
        log.info(f"Instance '{name}' deleted.")

    def list_instances(self) -> list[dict]:
        try:
            paginator = self.rds.get_paginator("describe_db_instances")
            instances = []
            for page in paginator.paginate(
                Filters=[{"Name": "tag:managed-by", "Values": ["pg-provision"]}]
            ):
                for db in page["DBInstances"]:
                    name_tag = next(
                        (t["Value"] for t in db.get("TagList", [])
                         if t["Key"] == "instance-name"),
                        db["DBInstanceIdentifier"]
                    )
                    endpoint = db.get("Endpoint", {})
                    status = db["DBInstanceStatus"]
                    instances.append({
                        "name": name_tag,
                        "status": "running" if status == "available" else status,
                        "version": db["EngineVersion"],
                        "host": endpoint.get("Address", "—"),
                        "port": endpoint.get("Port", "—"),
                        "created": db.get("InstanceCreateTime", "—"),
                    })
            return instances
        except ClientError as e:
            raise RuntimeError(f"RDS DescribeDBInstances failed: {e}") from e
