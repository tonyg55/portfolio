terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to use S3 backend
  # backend "s3" {
  #   bucket         = "your-tfstate-bucket"
  #   key            = "pg-provision/dev/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Environment = "dev"
      ManagedBy   = "terraform"
      Project     = "pg-provision"
    }
  }
}

module "vpc" {
  source = "../../modules/vpc"

  name            = "pg-provision-dev"
  cidr            = "10.0.0.0/16"
  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  tags = { Environment = "dev" }
}

module "postgres_dev" {
  source = "../../modules/rds"

  identifier     = "pg-provision-dev"
  engine_version = var.pg_version
  instance_class = "db.t3.micro"
  allocated_storage     = 20
  max_allocated_storage = 50

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = module.vpc.db_subnet_group_name
  vpc_security_group_ids = [module.vpc.rds_security_group_id]

  backup_retention_period = 3
  multi_az                = false
  deletion_protection     = false
  skip_final_snapshot     = true

  performance_insights_enabled = false
  monitoring_interval          = 0

  tags = { Environment = "dev" }
}

output "db_endpoint" {
  description = "PostgreSQL endpoint"
  value       = module.postgres_dev.endpoint
}

output "db_address" {
  value = module.postgres_dev.address
}
