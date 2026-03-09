#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_BIN="$ROOT_DIR/dist/ccd"
INSTALL_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
ICON_FILE="${ICON_DIR}/cococartdump.png"
APP_FILE="${APP_DIR}/cococartdump.desktop"

if [[ ! -f "$DIST_BIN" ]]; then
  echo "Missing $DIST_BIN"
  echo "Build it first with scripts/build_linux.sh"
  exit 1
fi

mkdir -p "$INSTALL_DIR" "$APP_DIR" "$ICON_DIR"
install -m 755 "$DIST_BIN" "${INSTALL_DIR}/ccd"
install -m 644 "$ROOT_DIR/scripts/coco.png" "$ICON_FILE"

cat > "$APP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=CoCo Cart Dumper
Comment=Standalone TRS-80 Color Computer cartridge dumper
Exec=${INSTALL_DIR}/ccd
Icon=${ICON_FILE}
Terminal=false
Categories=Utility;
EOF

chmod 644 "$APP_FILE"

echo "Installed:"
echo "  Binary: ${INSTALL_DIR}/ccd"
echo "  Icon: ${ICON_FILE}"
echo "  Desktop entry: ${APP_FILE}"
echo
echo "If ${INSTALL_DIR} is not in PATH, add this line to your shell profile:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
