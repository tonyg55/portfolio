resource "aws_db_parameter_group" "this" {
  name   = "${var.identifier}-pg"
  family = var.parameter_group_family

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_lock_waits"
    value = "1"
  }

  parameter {
    name  = "autovacuum"
    value = "1"
  }

  parameter {
    name  = "track_activity_query_size"
    value = "4096"
  }

  tags = var.tags
}

resource "aws_iam_role" "rds_enhanced_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  name  = "${var.identifier}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
    }]
  })

  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"]
  tags                = var.tags
}

resource "aws_db_instance" "this" {
  identifier        = var.identifier
  engine            = "postgres"
  engine_version    = var.engine_version
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage

  max_allocated_storage = var.max_allocated_storage > 0 ? var.max_allocated_storage : null

  db_name  = var.db_name
  username = var.username
  password = var.password

  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = var.vpc_security_group_ids
  parameter_group_name   = aws_db_parameter_group.this.name

  storage_type      = "gp3"
  storage_encrypted = true

  multi_az            = var.multi_az
  publicly_accessible = false

  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window

  deletion_protection = var.deletion_protection
  skip_final_snapshot = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.identifier}-final"

  performance_insights_enabled          = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_enabled ? 7 : null

  monitoring_interval = var.monitoring_interval
  monitoring_role_arn = var.monitoring_interval > 0 ? aws_iam_role.rds_enhanced_monitoring[0].arn : null

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true

  tags = merge(var.tags, { managed-by = "pg-provision" })

  lifecycle {
    prevent_destroy = false
    ignore_changes  = [password] # Managed outside Terraform after initial creation
  }
}
