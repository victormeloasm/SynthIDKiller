#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./quick_run.sh IMAGE [OUTPUT_DIR]"
  exit 1
fi

IMAGE="$1"
OUTPUT="${2:-frog_results}"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Warning: no active virtual environment detected."
  echo "Recommended:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  python -m pip install -r requirements.txt"
  echo
fi

python run_photo_all.py "$IMAGE" --output "$OUTPUT" --preset balanced --fast
