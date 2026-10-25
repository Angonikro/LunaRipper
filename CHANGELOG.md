## 0.3.5

- Ausgabeauswahl in der bestätigten Reihenfolge: MP3, OGG, M4A, WAV, OGG + WAV, MP3 + WAV, M4A + WAV, MP3 + OGG, OGG + M4A, MP3 + M4A, MP3 + WAV + OGG, OGG + WAV + M4A, MP3 + WAV + M4A, MP3 + OGG + M4A, MP3 + OGG + WAV + M4A.
- M4A/AAC-Ausgabe über `ffmpeg`, inklusive MP4-Metadaten und Cover.
- Neue Laufzeitabhängigkeit `ffmpeg` dokumentiert und im DEB eingetragen; APT installiert sie automatisch.
- Ausgabeformate um OGG Vorbis und alle gewünschten Formatkombinationen erweitert. Reihenfolge: MP3, OGG, WAV, OGG + WAV, MP3 + WAV, MP3 + OGG, MP3 + WAV + OGG.
- OGG-Metadaten für Titel, Interpret, Album, Tracknummer und Jahr werden geschrieben.
- Neue Abhängigkeit: `vorbis-tools` (stellt `oggenc` bereit); Installationsanleitung und Debian-Abhängigkeiten aktualisiert.
- Ausgabeformat MP3, WAV oder MP3 + WAV hinzugefügt; Auswahl wird in den Einstellungen gespeichert.
- WAV-Dateien werden ohne zusätzlichen Encoder aus dem CD-Audio-Ausleseergebnis übernommen.
- M3U-Playlist verwendet bei WAV-Ausgabe WAV-Dateien, sonst MP3-Dateien.

## 0.3.4
- Desktop Launcher hinzugefügt

## 0.3.3
- Save and restore the M3U playlist checkbox in `~/.config/lunaripper/settings.json`.

## 0.3.2 - 2026-10-24

- Add an optional M3U playlist checkbox (disabled by default).
- Write the playlist only after successful ripping and include only selected MP3 files that exist.
- Keep the GitHub ZIP source-only; the Debian package is built separately.

## 0.3.1 - 2026-10-24
- Neue Schaltfläche „CD auswerfen“ für das aktuell ausgewählte optische Laufwerk.
- Verständliche Statusmeldung bei Erfolg, fehlendem `eject`-Programm, Zeitüberschreitung oder Fehler.
- Debian-Paket installiert die Abhängigkeit `eject` automatisch.

## 0.3.0 - 2026-10-24
- GitHub-Release auf Basis von LunaRipper 0.2.22.
- Gesamte Audio-CD: längeres, an der Anzahl der Tracks orientiertes cdparanoia-Zeitlimit, damit vollständige Alben nicht vorzeitig abbrechen.
- Trackreihenfolge und Titelnamen bleiben beim Auswählen eines Covers erhalten.
- Beibehaltung des direkten Schreibens unter dem endgültigen MP3-Dateinamen; kein zusätzlicher temporärer MP3-/Hardlink-Schritt.
- Paketstruktur, Startskript und Dokumentation für den Release ergänzt.

## 0.2.22 - 2026-10-24
- Fix: Full-CD ripping no longer uses a timeout based only on the two endpoints of a track range.
- Give cdparanoia a timeout based on the actual number of tracks, allowing full albums and slower/scratched discs more time.
- Preserve selected-track reading, cancel support, direct final MP3 filename writing, and the 0.2.21 cover/order fix.

## 0.2.21 - 2026-10-23
- Fix: Cover/album lookup no longer overwrites CD track titles or changes their order.
- Preserve the track names detected during CDDB/CD identification while choosing cover art.
- Keep direct final MP3 filename writing and selected-track ripping behavior.

## 0.2.20 - 2026-10-23
- CDDB-Titelnamen werden anhand der tatsächlichen CD-Tracknummer zugeordnet (TTITLE0 = Track 1), nicht nur anhand der Listenposition.
- MusicBrainz-Titelnamen werden ebenfalls anhand der Tracknummer zugeordnet, damit Titel und Audiodatei nicht durch abweichende Listenreihenfolge vertauscht werden.
- Bewährtes direktes Schreiben unter dem endgültigen MP3-Dateinamen bleibt erhalten; Abbrechen und gezieltes Auslesen bleiben erhalten.

## 0.2.19 - 2026-10-23
- Fehlerhafte Übergabe mehrerer Tracknummern an cdparanoia korrigiert: zusammenhängende Auswahl wird als Trackbereich (z. B. `1-2`) übergeben.
- Nicht zusammenhängende Auswahl (z. B. `1` und `15`) wird in getrennten Bereichen gelesen; nicht ausgewählte Tracks werden nicht absichtlich ausgelesen.
- Abbrechen-Funktion und Startmenü-Icon aus 0.2.18 bleiben erhalten.

## 0.2.18 - 2026-10-23
- Abbrechen-Schaltfläche während des Rippens hinzugefügt.
- Laufende cdparanoia- und lame-Prozesse können beendet werden.
- Bereits fertig gespeicherte MP3-Dateien bleiben beim Abbruch erhalten; unvollständige .part-Dateien werden entfernt.
- Ausgewählte Tracks werden weiterhin gezielt gelesen.

## 0.2.17 - 2026-10-23
- Es werden nur die angehakten CD-Titel an cdparanoia übergeben.
- Auch Wiederholungs- und Rettungsversuche lesen ausschließlich ausgewählte Titel.
- Batch-Leseverfahren bleibt erhalten; MP3-Konvertierung erfolgt weiterhin pro ausgewähltem Titel.

## 0.2.16
- CDDB-Anbieterauswahl bereinigt.
