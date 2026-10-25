#!/bin/sh
set -eu
VERSION=0.3.5
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/lunaripper"
install -d "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/share/lunaripper/scripts" "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/scalable/apps"
install -m 755 "$ROOT/lunaripper.py" "$PKG/usr/share/lunaripper/lunaripper.py"
install -m 755 "$ROOT/scripts/create_desktop_entry.sh" "$PKG/usr/share/lunaripper/scripts/create_desktop_entry.sh"
install -m 644 "$ROOT/lunaripper.svg" "$PKG/usr/share/lunaripper/lunaripper.svg"
cat > "$PKG/usr/bin/lunaripper" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/lunaripper/lunaripper.py "$@"
EOF
chmod 755 "$PKG/usr/bin/lunaripper"
cat > "$PKG/usr/bin/lunaripper-desktop-launcher" <<'EOF'
#!/bin/sh
exec /usr/share/lunaripper/scripts/create_desktop_entry.sh "$@"
EOF
chmod 755 "$PKG/usr/bin/lunaripper-desktop-launcher"
cat > "$PKG/usr/share/applications/lunaripper.desktop" <<'EOF'
[Desktop Entry]
Name=LunaRipper
Comment=Audio-CD-Ripper mit Metadaten und MP3-Ausgabe
Exec=lunaripper
Icon=lunaripper
Terminal=false
Type=Application
Categories=AudioVideo;Audio;
EOF
install -m 644 "$ROOT/lunaripper.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/lunaripper.svg"
cat > "$PKG/DEBIAN/control" <<EOF
Package: lunaripper
Version: $VERSION
Section: sound
Priority: optional
Architecture: all
Depends: python3, python3-gi, gir1.2-gtk-4.0, python3-mutagen, cdparanoia, cd-discid, lame, eject, vorbis-tools, ffmpeg
Maintainer: LunaRipper contributors
Description: Audio-CD-Ripper mit Metadaten und MP3/OGG/M4A/WAV-Ausgabe
 LunaRipper liest Audio-CDs aus und speichert Tracks als MP3, OGG, M4A, WAV oder in Kombinationen.
EOF
dpkg-deb --root-owner-group --build "$PKG" "$ROOT/lunaripper_${VERSION}_all.deb"
