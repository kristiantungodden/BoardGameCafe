#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
REQUIREMENTS_FILE="$PROJECT_ROOT/boardgame_cafe/requirements.txt"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Virtual environment not found at .venv"
  echo "Create it first: python3 -m venv .venv"
  exit 1
fi

if [[ "${1:-}" == "--install-deps" ]]; then
  "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"
fi

"$VENV_PYTHON" -m flask --app run.py run --debug
