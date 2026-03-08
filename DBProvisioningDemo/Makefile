.PHONY: help install up down provision-local list health backup fmt lint test clean

PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker compose
INSTANCE_NAME ?= demo-pg

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dependencies
	$(PIP) install -r requirements.txt

up:  ## Start local PostgreSQL + monitoring stack
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml \
		-f docker/docker-compose.monitoring.yml up -d
	@echo "PostgreSQL  → localhost:5432"
	@echo "Prometheus  → http://localhost:9090"
	@echo "Grafana     → http://localhost:3000  (admin/changeme)"
	@echo "PG Exporter → http://localhost:9187/metrics"

down:  ## Stop and remove local stack
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml \
		-f docker/docker-compose.monitoring.yml down -v

provision-local:  ## Provision a named local instance
	$(PYTHON) main.py provision --target local --name $(INSTANCE_NAME) \
		--db-name appdb --username appuser --password localpass --version 16

list:  ## List local instances
	$(PYTHON) main.py list --target local

health:  ## Health-check the local instance
	$(PYTHON) main.py health --host localhost --port 5432 \
		--db-name appdb --username appuser --password localpass

backup:  ## Backup the local database
	$(PYTHON) main.py backup --host localhost --port 5432 \
		--db-name appdb --username appuser --password localpass \
		--output backups/$(INSTANCE_NAME)-$(shell date +%Y%m%d-%H%M%S).dump

fmt:  ## Format Python code
	black src/ main.py

lint:  ## Lint Python code
	flake8 src/ main.py --max-line-length=120

test:  ## Run tests
	pytest tests/ -v

tf-init:  ## Terraform init (dev env)
	terraform -chdir=terraform/environments/dev init

tf-plan:  ## Terraform plan (dev env)
	terraform -chdir=terraform/environments/dev plan

tf-apply:  ## Terraform apply (dev env)
	terraform -chdir=terraform/environments/dev apply

clean:  ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache/ dist/ build/
