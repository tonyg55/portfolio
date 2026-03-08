output "endpoint" {
  description = "RDS endpoint address"
  value       = aws_db_instance.this.endpoint
}

output "address" {
  description = "RDS hostname"
  value       = aws_db_instance.this.address
}

output "port" {
  description = "RDS port"
  value       = aws_db_instance.this.port
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.this.db_name
}

output "identifier" {
  description = "RDS instance identifier"
  value       = aws_db_instance.this.identifier
}

output "arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.this.arn
}
