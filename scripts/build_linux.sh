#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN_DIR="$ROOT_DIR/scripts/.venv/bin"

cd "$ROOT_DIR"

PYINSTALLER_CMD=()
if [[ -x "$VENV_BIN_DIR/pyinstaller" ]]; then
  PYINSTALLER_CMD=("$VENV_BIN_DIR/pyinstaller")
elif command -v pyinstaller >/dev/null 2>&1; then
  PYINSTALLER_CMD=(pyinstaller)
elif [[ -x "$VENV_BIN_DIR/python" ]] && "$VENV_BIN_DIR/python" -c "import PyInstaller" >/dev/null 2>&1; then
  PYINSTALLER_CMD=("$VENV_BIN_DIR/python" -m PyInstaller)
elif python3 -c "import PyInstaller" >/dev/null 2>&1; then
  PYINSTALLER_CMD=(python3 -m PyInstaller)
else
  echo "PyInstaller is not available."
  echo "Install it with:"
  echo "  python3 -m pip install -r requirements-build.txt"
  echo
  echo "If your distro blocks user installs, create a virtual environment first:"
  echo "  python3 -m venv .venv"
  echo "  . .venv/bin/activate"
  echo "  python3 -m pip install -r requirements-build.txt"
  exit 1
fi

"${PYINSTALLER_CMD[@]}" \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --icon scripts/coco.png \
  --name ccd \
  tools/capture_coco_dump.py

echo "Build complete: $ROOT_DIR/dist/ccd"
