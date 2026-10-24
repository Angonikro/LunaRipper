#!/bin/sh
set -eu
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
if [ -f "$HOME/.config/user-dirs.dirs" ]; then
    configured=$(sed -n 's/^XDG_DESKTOP_DIR="\(.*\)"/\1/p' "$HOME/.config/user-dirs.dirs" | head -n 1)
    if [ -n "$configured" ]; then
        case "$configured" in
            '$HOME'/*) configured="$HOME/${configured#'$HOME'/}" ;;
            '$HOME') configured="$HOME" ;;
        esac
        DESKTOP_DIR="$configured"
    fi
fi
mkdir -p "$DESKTOP_DIR"
LAUNCHER="$DESKTOP_DIR/LunaRipper.desktop"
cat > "$LAUNCHER" <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=LunaRipper
Comment=Audio-CDs auslesen und als MP3 speichern
Exec=lunaripper
Icon=lunaripper
Terminal=false
Categories=AudioVideo;Audio;
StartupNotify=true
EOF
chmod +x "$LAUNCHER"
printf 'Desktoplauncher erstellt: %s\n' "$LAUNCHER"
printf 'LunaRipper muss installiert sein, damit der Launcher startet.\n'
