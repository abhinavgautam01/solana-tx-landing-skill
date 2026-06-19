#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_repo.py

