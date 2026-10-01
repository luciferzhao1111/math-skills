#!/usr/bin/env bash
# Verify everything the pipeline needs. Prints OK / MISSING per item and the fix. Exit code 1 if anything is missing.
#   bash setup_check.sh <project_dir>
set -uo pipefail
P="$(cd "${1:-.}" && pwd)"; bad=0
ok()   { printf '  OK       %s\n' "$1"; }
miss() { printf '  MISSING  %s\n           fix: %s\n' "$1" "$2"; bad=1; }
up() { d="$P"; while [ "$d" != "/" ]; do [ -e "$d/$1" ] && { echo "$d"; return 0; }; d="$(dirname "$d")"; done; return 1; }

echo "project: $P"
PY=""
for c in /usr/bin/python3 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import numpy, requests, pypinyin" 2>/dev/null; then PY="$(command -v "$c")"; break; fi
done
[ -n "$PY" ] && ok "python with numpy+requests+pypinyin: $PY   (use this as PY)" \
  || miss "python3 with numpy, requests, pypinyin" "python3 -m pip install --user numpy requests pypinyin pillow"
[ -n "$PY" ] && { "$PY" -c "import PIL" 2>/dev/null && ok "pillow (problem image tools)" || miss "pillow" "$PY -m pip install --user pillow"; }
command -v node >/dev/null && ok "node $(node -v)" || miss "node" "install Node.js 18+"
NM="$(up node_modules/playwright)" && ok "playwright in $NM/node_modules" || miss "playwright (shared node_modules)" "cd <workspace_root> && npm install   (package.json made by new_video.sh)"
FF="$(up node_modules/ffmpeg-static/ffmpeg)" && ok "ffmpeg-static in $FF/node_modules" || miss "ffmpeg-static" "cd <workspace_root> && npm install"
if [ -d "/Applications/Google Chrome.app" ] || command -v google-chrome >/dev/null 2>&1; then ok "Google Chrome"; else
  echo "  note     no Google Chrome: render.mjs falls back to Playwright Chromium -> run: npx playwright install chromium"; fi
PR="$(up pron.py)" && [ -e "$PR/pron.json" ] && ok "pron.py + pron.json in $PR" || miss "pron.py + pron.json" "copy <skill>/shared/pron.* to the workspace root"
ENVD="$(up .env)"; UENV="$HOME/.config/math-problem-video/.env"
if [ -n "${GLM_API_KEY:-}" ]; then ok "GLM_API_KEY in environment"
elif [ -n "$ENVD" ] && grep -q '^GLM_API_KEY=..' "$ENVD/.env"; then ok "GLM_API_KEY in $ENVD/.env (value not shown)"
elif [ -f "$UENV" ] && grep -q '^GLM_API_KEY=..' "$UENV"; then ok "GLM_API_KEY in $UENV (value not shown)"
else miss "GLM_API_KEY" "ASK THE USER to add a line GLM_API_KEY=<key> to $UENV (all directories) or <workspace_root>/.env. Key: https://bigmodel.cn/usercenter/proj-mgmt/apikeys. See reference/glm-tts-setup.md. Do NOT go looking for another project's .env."; fi
V="$( { [ -f "$UENV" ] && grep '^GLM_VOICE=' "$UENV"; [ -n "$ENVD" ] && grep '^GLM_VOICE=' "$ENVD/.env"; } 2>/dev/null | tail -1 | cut -d= -f2 )"
echo "  voice    ${GLM_VOICE:-${V:-tongtong (default)}}"
[ $bad -eq 0 ] && echo "ALL OK. Next: key test ->  cd $P && ${PY:-python3} build_audio.py --say \"你好，我们来看一道数学题。\"" || echo "Fix the MISSING items, then run this again."
exit $bad
