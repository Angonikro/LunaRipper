#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
APP_PATH="$PROJECT_DIR/lunaripper.py"
PROJECT_ICON="$PROJECT_DIR/lunaripper.svg"
SYSTEM_ENTRY="/usr/share/applications/lunaripper.desktop"
SYSTEM_ICON="/usr/share/icons/hicolor/scalable/apps/lunaripper.svg"

# Honor XDG desktop folder settings; use POSIX shell syntax only.
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
if [ -f "$HOME/.config/user-dirs.dirs" ]; then
    . "$HOME/.config/user-dirs.dirs"
    if [ -n "${XDG_DESKTOP_DIR:-}" ]; then
        case "$XDG_DESKTOP_DIR" in
            '$HOME'/*) DESKTOP_DIR="$HOME/$(printf '%s' "$XDG_DESKTOP_DIR" | sed "s|^\\$HOME/||")" ;;
            '$HOME') DESKTOP_DIR="$HOME" ;;
            *) DESKTOP_DIR="$XDG_DESKTOP_DIR" ;;
        esac
    fi
fi
mkdir -p "$DESKTOP_DIR"
DEST="$DESKTOP_DIR/LunaRipper.desktop"

if [ -r "$SYSTEM_ENTRY" ] && [ -x /usr/bin/lunaripper ]; then
    cp "$SYSTEM_ENTRY" "$DEST"
    # Absolute icon path makes the custom icon resolvable on the desktop.
    if [ -r "$SYSTEM_ICON" ]; then
        if grep -q '^Icon=' "$DEST"; then
            sed "s|^Icon=.*|Icon=$SYSTEM_ICON|" "$DEST" > "$DEST.tmp"
            mv "$DEST.tmp" "$DEST"
        else
            printf '\nIcon=%s\n' "$SYSTEM_ICON" >> "$DEST"
        fi
    fi
else
    if [ ! -r "$APP_PATH" ]; then
        echo "LunaRipper application file not found: $APP_PATH" >&2
        exit 1
    fi
    if [ -r "$PROJECT_ICON" ]; then
        ICON_PATH="$PROJECT_ICON"
    else
        ICON_PATH="audio-cd"
    fi
    printf '[Desktop Entry]\nName=LunaRipper\nComment=Audio-CD-Ripper mit Metadaten und MP3-Ausgabe\nExec=python3 "%s"\nIcon=%s\nTerminal=false\nType=Application\nCategories=AudioVideo;Audio;\n' "$APP_PATH" "$ICON_PATH" > "$DEST"
fi

chmod +x "$DEST"
echo "Desktop launcher created: $DEST"
echo "Icon: $(grep '^Icon=' "$DEST" | tail -n 1 | cut -d= -f2-)"
