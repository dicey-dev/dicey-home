#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
case "${1:-}" in
  "")
    python3 -B -m unittest discover -s tests -p 'test_*.py'
    node tests/test_launcher.js
    node tests/test_home.js
    ;;
  --compat)
    # This layer intentionally requires the actual installed Omarchy menu.
    node tests/test_menu_compatibility.js
    ;;
  *) echo "Usage: tests/run.sh [--compat]" >&2; exit 2 ;;
esac
