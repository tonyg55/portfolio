terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "YOUR_TFSTATE_BUCKET"
    key            = "pg-provision/prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Environment = "prod"
      ManagedBy   = "terraform"
      Project     = "pg-provision"
    }
  }
}

module "vpc" {
  source = "../../modules/vpc"

  name            = "pg-provision-prod"
  cidr            = "10.1.0.0/16"
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
  public_subnets  = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]

  tags = { Environment = "prod" }
}

module "postgres_prod" {
  source = "../../modules/rds"

  identifier     = "pg-provision-prod"
  engine_version = var.pg_version
  instance_class = "db.r6g.large"
  allocated_storage     = 100
  max_allocated_storage = 500

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = module.vpc.db_subnet_group_name
  vpc_security_group_ids = [module.vpc.rds_security_group_id]

  backup_retention_period = 14
  multi_az                = true
  deletion_protection     = true
  skip_final_snapshot     = false

  performance_insights_enabled = true
  monitoring_interval          = 60

  tags = { Environment = "prod" }
}

output "db_endpoint" {
  value = module.postgres_prod.endpoint
}
