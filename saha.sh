#!/usr/bin/env bash
# Saha - Agentic loop orchestrator
# This script bootstraps the environment and runs the saha CLI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[saha]${NC} $1"; }
warn() { echo -e "${YELLOW}[saha]${NC} $1"; }
error() { echo -e "${RED}[saha]${NC} $1" >&2; }

# Check if uv is installed, install if not
ensure_uv() {
    if command -v uv &> /dev/null; then
        return 0
    fi

    info "Installing uv (fast Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"

    if ! command -v uv &> /dev/null; then
        error "Failed to install uv. Please install manually: https://docs.astral.sh/uv/"
        exit 1
    fi

    info "uv installed successfully"
}

# Ensure venv and dependencies are set up
ensure_env() {
    if [ ! -d ".venv" ]; then
        info "Setting up Python environment..."
        uv venv --python 3.12 2>/dev/null || uv venv --python 3.11 2>/dev/null || uv venv
        info "Installing dependencies..."
        uv pip install -e ".[dev,tools]" --quiet
        info "Environment ready"
    fi
}

# Main
ensure_uv
ensure_env

# Run saha with all arguments using the venv directly
exec .venv/bin/saha "$@"
