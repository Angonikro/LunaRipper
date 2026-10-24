#!/bin/sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
chmod +x "$SCRIPT_DIR/scripts/create_desktop_entry.sh"
exec "$SCRIPT_DIR/scripts/create_desktop_entry.sh"
