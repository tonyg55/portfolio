#!/usr/bin/env bash
# Bootstrap the local development environment
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[bootstrap]${NC} $*"; }
warn()  { echo -e "${YELLOW}[bootstrap]${NC} $*"; }

# ── Checks ─────────────────────────────────────────────────────────────────────
command -v docker   >/dev/null 2>&1 || { echo "docker not found. Install Docker Desktop."; exit 1; }
command -v python3  >/dev/null 2>&1 || { echo "python3 not found."; exit 1; }

# ── Python virtualenv ──────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  info "Creating Python virtual environment..."
  python3 -m venv .venv
fi

info "Activating venv and installing dependencies..."
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# ── .env ───────────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  info "Copying .env.example → .env"
  cp .env.example .env
  warn "Review .env and set your values before running."
fi

# ── Backups dir ────────────────────────────────────────────────────────────────
mkdir -p backups

info "Bootstrap complete. Run 'make up' to start the local stack."
