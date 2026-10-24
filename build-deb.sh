#!/bin/sh
set -eu
VERSION=0.3.3
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/lunaripper"
install -d "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/share/lunaripper" "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/scalable/apps"
install -m 755 "$ROOT/lunaripper.py" "$PKG/usr/share/lunaripper/lunaripper.py"
cat > "$PKG/usr/bin/lunaripper" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/lunaripper/lunaripper.py "$@"
EOF
chmod 755 "$PKG/usr/bin/lunaripper"
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
cat > "$PKG/usr/share/icons/hicolor/scalable/apps/lunaripper.svg" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><rect x="8" y="8" width="112" height="112" rx="24" fill="#253858"/><circle cx="64" cy="64" r="38" fill="#dce6f2"/><circle cx="64" cy="64" r="13" fill="#253858"/><circle cx="64" cy="64" r="4" fill="#dce6f2"/><path d="M64 26 A38 38 0 0 1 102 64" fill="none" stroke="#6bc4a6" stroke-width="5"/></svg>
EOF
cat > "$PKG/DEBIAN/control" <<EOF
Package: lunaripper
Version: $VERSION
Section: sound
Priority: optional
Architecture: all
Depends: python3, python3-gi, gir1.2-gtk-4.0, python3-mutagen, cdparanoia, cd-discid, lame, eject
Maintainer: LunaRipper contributors
Description: Audio-CD-Ripper mit Metadaten und MP3-Ausgabe
 LunaRipper liest Audio-CDs aus und speichert Tracks als MP3.
EOF
dpkg-deb --root-owner-group --build "$PKG" "$ROOT/lunaripper_${VERSION}_all.deb"
