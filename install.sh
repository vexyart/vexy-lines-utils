#!/usr/bin/env bash
# install.sh - Install vexy-lines-utils in editable mode
# Vexy Lines is a macOS vector art application.
# Shared utilities and helper functions for the Vexy Lines ecosystem.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing vexy-lines-utils in editable mode..."
uv pip install --system -e .

echo "==> Install complete."
