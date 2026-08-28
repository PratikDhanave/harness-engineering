#!/usr/bin/env bash
# Set up this repo on macOS or Linux. Safe to re-run.
#   ./scripts/install.sh
# Then, once, if you want the on-device model ready before you need it:
#   uv run python3 scripts/prefetch_model.py     (~2-3 GB, one time)
set -eu
cd "$(dirname "$0")/.."

command -v git >/dev/null || { echo "install git first"; exit 1; }

if ! command -v uv >/dev/null; then
  echo "installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

echo "installing dependencies (uv brings its own Python)..."
uv sync --extra dev

echo "verifying..."
uv run --extra dev pytest -q
uv run python3 scripts/af_tour.py >/dev/null 2>&1 && echo "all seven lessons ran"

echo
echo "ready:"
echo "  make test                            the suite"
echo "  uv run python3 scripts/af_tour.py    all seven lessons"
echo "  make run                             API on :8000"
echo "  make run-local                       /chat on an on-device model"
