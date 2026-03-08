variable "identifier" {
  description = "RDS instance identifier"
  type        = string
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.2"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Initial storage allocation in GiB"
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Maximum storage for autoscaling (0 = disabled)"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Initial database name"
  type        = string
}

variable "username" {
  description = "Master username"
  type        = string
}

variable "password" {
  description = "Master password"
  type        = string
  sensitive   = true
}

variable "db_subnet_group_name" {
  description = "DB subnet group name"
  type        = string
}

variable "vpc_security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "parameter_group_family" {
  description = "Parameter group family"
  type        = string
  default     = "postgres16"
}

variable "backup_retention_period" {
  description = "Days to retain automated backups"
  type        = number
  default     = 7
}

variable "backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window"
  type        = string
  default     = "Mon:04:00-Mon:05:00"
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on deletion"
  type        = bool
  default     = true
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0=disabled)"
  type        = number
  default     = 60
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
