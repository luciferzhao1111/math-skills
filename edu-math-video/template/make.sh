#!/usr/bin/env bash
# Full build: lint + pronunciation check -> TTS + mix -> stills for review -> video.
# Usage: ./make.sh [workers]      (PY=/path/to/python3 ./make.sh to choose the interpreter)
set -euo pipefail
cd "$(dirname "$0")"
if [ -z "${PY:-}" ]; then
  if /usr/bin/python3 -c "import numpy, requests, pypinyin" 2>/dev/null; then PY=/usr/bin/python3; else PY=python3; fi
fi
"$PY" build_audio.py --check
"$PY" build_audio.py
node render.mjs motion
node render.mjs stills auto
node render.mjs video "${1:-6}"
