#!/usr/bin/env python3
"""LunaRipper - simple GTK 4 audio CD ripper for Linux."""
import os
import re
import json
import glob
import subprocess
import shutil
import threading
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gio, Gdk
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, APIC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4, MP4Cover

APP_VERSION = '0.3.6'
USER_AGENT = 'LunaRipper/0.3.6 (GTK audio CD ripper)'

TRANSLATIONS = {
    'en': {
        'Audio-CDs auslesen · Metadaten · Cover · MP3 · M4A · OGG · WAV': 'Rip audio CDs · metadata · cover art · MP3 · M4A · OGG · WAV',
        'Audio-CD': 'Optical drive', 'Laufwerk:': 'Drive:', 'noch nicht eingelesen': 'not scanned yet',
        'CD einlesen': 'Read disc', 'Laufwerk suchen': 'Refresh drives', 'CD auswerfen': 'Eject CD', 'Albumdaten': 'Album information',
        'Interpret': 'Artist', 'Albumtitel': 'Album title', 'Jahr': 'Year',
        'Interpret oder Künstler': 'Artist or performer', 'z. B. 1985': 'e.g. 1985',
        'Daten & Cover suchen': 'Find metadata & cover', 'Cover noch nicht geladen': 'Cover not loaded',
        'Cover gefunden': 'Cover found', 'Titel auswählen': 'Select tracks',
        'Lies zuerst eine Audio-CD ein.': 'Read an audio CD first.', 'Alle auswählen': 'Select all',
        'Keine auswählen': 'Select none', 'Speicherort': 'Output folder', 'Durchsuchen …': 'Browse…',
        'Im Zielordner entsteht genau ein Albumordner: „Interpret - Albumtitel“.': 'One album folder is created in the destination: “Artist - Album title”.',
        'MP3-Qualität:': 'MP3 quality:', 'M3U-Playlist erstellen': 'Create M3U playlist', '💿 Ausgewählte Titel rippen': '💿 Rip selected tracks',
        'Bereit.': 'Ready.', 'Sprache:': 'Language:', 'Dunkles Design verwenden': 'Use dark theme',
        'Deutsch': 'German', 'Englisch': 'English', 'Dunkel': 'Dark theme',
        'Kein optisches Laufwerk gefunden': 'No optical drive found', 'optisches Laufwerk': 'optical drive',
        'CD-Laufwerk wurde ausgeworfen.': 'CD drive ejected.', 'CD konnte nicht ausgeworfen werden.': 'Could not eject the CD.', 'Das Programm „eject“ fehlt. Bitte das Paket eject installieren.': 'The eject program is missing. Please install the eject package.', 'Zeitüberschreitung beim Auswerfen der CD.': 'Timed out while ejecting the CD.',
        'Laufwerkssuche abgeschlossen.': 'Drive scan complete.', 'Kein optisches Laufwerk gefunden. Bitte Laufwerk suchen.': 'No optical drive found. Please refresh the drive list.',
        'Kein optisches Laufwerk gefunden.': 'No optical drive found.', 'Lies zuerst eine Audio-CD ein.': 'Read an audio CD first.',
        'Bitte mindestens einen Titel auswählen.': 'Please select at least one track.',
        'Bitte einen Speicherordner auswählen.': 'Please choose an output folder.',
        'Hilfe': 'Help', 'Anleitung': 'User guide', 'Info': 'About',
        'Bitte Interpret und Albumtitel eintragen, damit wir Metadaten und Cover suchen können.': 'Enter artist and album title to search for metadata and cover art.',
        'Suche bei MusicBrainz und Cover Art Archive …': 'Searching MusicBrainz and Cover Art Archive…',
        'Kein passender Eintrag gefunden. Interpret und Albumtitel bleiben wie eingegeben; du kannst trotzdem rippen.': 'No matching release found. You can still rip using the entered details.',
        'Metadaten gefunden. Bitte kontrolliere Interpret, Album und Titelnamen vor dem Rippen.': 'Metadata found. Check artist, album and track titles before ripping.',
        'Metadatensuche fehlgeschlagen:': 'Metadata search failed:',
        'Cover gefunden': 'Cover found', 'Metadaten gefunden · kein Cover verfügbar': 'Metadata found · no cover available',
        'Audio-CD wird untersucht …': 'Scanning audio CD…', 'Bereit.': 'Ready.',
        'Titel auswählen': 'Select tracks', 'Interpret oder Künstler': 'Artist or performer',
        'Unbekannter Interpret': 'Unknown artist', 'Unbekanntes Album': 'Unknown album',
        'Laufwerk:': 'Drive:', 'Titel erkannt.': 'tracks detected.',
        'Daten & Cover suchen': 'Find metadata & cover', 'Speicherordner auswählen': 'Choose output folder',
        'Auswählen': 'Select', 'Abbrechen': 'Cancel',
        'Keine Audio-CD-Titel erkannt. Bitte CD einlegen und Laufwerk prüfen. Details: ': 'No audio CD tracks detected. Insert a disc and check the drive. Details: ',
        'CD-Daten automatisch zugeordnet.': 'CD metadata matched automatically.',
        'Wenn die CD nicht automatisch erkannt wurde, trage Interpret und Album ein und suche Daten & Cover.': 'If the disc was not matched automatically, enter the artist and album and search for metadata and cover art.',
        'Bitte CD einlegen und Laufwerk prüfen.': 'Insert a disc and check the drive.',
        'Kein passender Eintrag gefunden. Interpret und Albumtitel bleiben wie eingegeben; du kannst trotzdem rippen.': 'No matching release found. The entered artist and album remain; you can still rip.',
        'Metadaten gefunden. Bitte kontrolliere Interpret, Album und Titelnamen vor dem Rippen.': 'Metadata found. Check the artist, album and track names before ripping.',
        'Übersprungen, Datei existiert bereits:': 'Skipped, file already exists:',
        'Fertig! Dateien gespeichert in:': 'Done! Files saved to:',
        'Audio-CD wird untersucht …': 'Scanning audio CD…',
        'Bitte mindestens einen Titel auswählen.': 'Please select at least one track.',
        'Bitte einen Speicherordner auswählen.': 'Please choose an output folder.',
    }
}


def xdg_music_dir():
    """Return XDG music directory from user-dirs.dirs, if configured."""
    cfg = Path.home() / '.config' / 'user-dirs.dirs'
    if cfg.exists():
        try:
            for line in cfg.read_text(errors='ignore').splitlines():
                if line.strip().startswith('XDG_MUSIC_DIR='):
                    value = line.split('=', 1)[1].strip().strip('"').replace('$HOME', str(Path.home()))
                    p = Path(value).expanduser()
                    if p.exists() and p.is_dir():
                        return p
        except OSError:
            pass
    return None


def choose_default_music_dir():
    """Prefer the configured XDG music folder and never create Music/Musik duplicates."""
    configured = xdg_music_dir()
    if configured:
        return configured
    candidates = [Path.home() / 'Music', Path.home() / 'Musik']
    existing = [p for p in candidates if p.is_dir()]
    if len(existing) == 1:
        return existing[0]
    if len(existing) == 2:
        # If one contains files and the other is empty, prefer the populated folder.
        populated = []
        for p in existing:
            try:
                if any(p.iterdir()):
                    populated.append(p)
            except OSError:
                pass
        if len(populated) == 1:
            return populated[0]
        # If both are populated (or both empty), prefer the more recently used folder.
        try:
            return max(existing, key=lambda p: p.stat().st_mtime)
        except OSError:
            return existing[0]
    # Neither exists: use conventional English name as a suggested path, but don't create it yet.
    return Path.home() / 'Music'


def shutil_which(command):
    """Small PATH lookup without importing the full shutil module."""
    for directory in os.environ.get('PATH', '').split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def clean_name(value, fallback='Unknown'):
    value = (value or '').strip()
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', value)
    value = re.sub(r'\s+', ' ', value).strip(' .')
    return value or fallback


def run_command(args, timeout=None):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)


class LunaRipper(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='de.lunaripper.app', flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.tracks = []
        self.track_checks = []
        self.cover_bytes = None
        self.cover_candidates = []
        self.cover_source = 'none'
        self.release_id = None
        self.disc_id = None
        self.ripping = False
        self.cancel_requested = threading.Event()
        self.current_process = None
        self.config_dir = Path.home() / '.config' / 'lunaripper'
        self.config_file = self.config_dir / 'settings.json'
        self.music_dir = choose_default_music_dir()
        self.language = 'de'
        self.devices = []
        self.device = None
        self.dark_theme = True
        self.quality_index = 0
        self.auto_cddb = True
        self.cddb_provider = "dbpoweramp"
        self.cddb_server = "freedb.dbpoweramp.com"
        self.cddb_path = "/~cddb/cddb.cgi"
        self.cddb_port = "80"
        self.cddb_email = ""
        self.ignore_read_errors = False
        self.read_retries = 3
        self.create_m3u = False
        self.output_format = 'mp3'
        self.load_settings()
        self.refresh_devices()
        self._css_provider = None

    def load_settings(self):
        """Load user preferences from ~/.config/lunaripper/settings.json."""
        try:
            data = json.loads(self.config_file.read_text(encoding='utf-8'))
            if data.get('language') in ('de', 'en'):
                self.language = data['language']
            if isinstance(data.get('dark_theme'), bool):
                self.dark_theme = data['dark_theme']
            saved_folder = data.get('music_dir')
            if isinstance(saved_folder, str) and saved_folder.strip():
                self.music_dir = Path(saved_folder).expanduser()
            saved_device = data.get('device')
            if isinstance(saved_device, str) and saved_device:
                self.device = saved_device
            if data.get('quality_index') in (0, 1, 2):
                self.quality_index = data['quality_index']
            if isinstance(data.get('auto_cddb'), bool):
                self.auto_cddb = data['auto_cddb']
            if isinstance(data.get('ignore_read_errors'), bool):
                self.ignore_read_errors = data['ignore_read_errors']
            if data.get('read_retries') in (0, 1, 2, 3, 5):
                self.read_retries = data['read_retries']
            if isinstance(data.get('create_m3u'), bool):
                self.create_m3u = data['create_m3u']
            if data.get('output_format') in ('mp3', 'ogg', 'm4a', 'wav', 'ogg_wav', 'mp3_wav', 'm4a_wav', 'mp3_ogg', 'ogg_m4a', 'mp3_m4a', 'mp3_wav_ogg', 'ogg_wav_m4a', 'mp3_wav_m4a', 'mp3_ogg_m4a', 'mp3_ogg_wav_m4a'):
                self.output_format = data['output_format']
            elif data.get('output_format') == 'both':
                self.output_format = 'mp3_wav'
            if data.get('cddb_provider') in ('gnudb', 'musicbrainz', 'freac', 'dbpoweramp'):
                # Only keep the two providers that remain available in the UI.
                self.cddb_provider = data['cddb_provider'] if data['cddb_provider'] in ('freac', 'dbpoweramp') else 'dbpoweramp'
            for key, attr in (
                ('cddb_server', 'cddb_server'), ('cddb_path', 'cddb_path'),
                ('cddb_port', 'cddb_port'), ('cddb_email', 'cddb_email')
            ):
                value = data.get(key)
                if isinstance(value, str):
                    setattr(self, attr, value)
            # Upgrade previous default GNUDB settings to the tested compatible mirror.
            if data.get('cddb_provider', 'gnudb') == 'gnudb' and data.get('cddb_server', 'gnudb.gnudb.org') == 'gnudb.gnudb.org':
                self.cddb_provider = 'dbpoweramp'
                self.cddb_server = 'freedb.dbpoweramp.com'
                self.cddb_path = '/~cddb/cddb.cgi'
                self.cddb_port = '80'
        except (OSError, ValueError, TypeError):
            pass

    def save_settings(self):
        """Persist stable user preferences; never save album metadata or audio."""
        data = {
            'language': self.language,
            'dark_theme': self.dark_theme,
            'music_dir': str(self.music_dir),
            'device': self.device,
            'quality_index': self.quality_index,
            'auto_cddb': self.auto_cddb,
            'ignore_read_errors': self.ignore_read_errors,
            'read_retries': self.read_retries,
            'create_m3u': self.create_m3u,
            'output_format': self.output_format,
            'cddb_provider': self.cddb_provider,
            'cddb_server': self.cddb_server,
            'cddb_path': self.cddb_path,
            'cddb_port': self.cddb_port,
            'cddb_email': self.cddb_email,
        }
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            temp = self.config_file.with_suffix('.json.tmp')
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temp.replace(self.config_file)
        except OSError:
            pass

    def apply_theme(self):
        """Apply explicit GTK 4 colors so the switch works regardless of system theme."""
        if not hasattr(self, 'window'):
            return
        self.window.remove_css_class('lunaripper-dark')
        self.window.remove_css_class('lunaripper-light')
        self.window.add_css_class('lunaripper-dark' if self.dark_theme else 'lunaripper-light')
        display = Gdk.Display.get_default()
        if display and self._css_provider is None:
            provider = Gtk.CssProvider()
            provider.load_from_data(b"""
                /* Explicit high-contrast colors for every GTK control. */
                window.lunaripper-dark { background-color: #202124; color: #f1f3f4; }
                window.lunaripper-dark label, window.lunaripper-dark checkbutton,
                window.lunaripper-dark checkbutton label, window.lunaripper-dark radiobutton,
                window.lunaripper-dark radiobutton label, window.lunaripper-dark frame,
                window.lunaripper-dark frame > label { color: #f1f3f4; }
                window.lunaripper-dark entry, window.lunaripper-dark spinbutton,
                window.lunaripper-dark dropdown, window.lunaripper-dark dropdown button,
                window.lunaripper-dark button, window.lunaripper-dark menubutton > button {
                    background-color: #383a3e; background-image: none; color: #ffffff;
                    border-color: #62656b; text-shadow: none; box-shadow: none;
                }
                window.lunaripper-dark entry text { color: #ffffff; }
                window.lunaripper-dark entry placeholder { color: #c2c5ca; }
                window.lunaripper-dark list, window.lunaripper-dark row,
                window.lunaripper-dark scrolledwindow, window.lunaripper-dark textview,
                window.lunaripper-dark textview text { background-color: #252629; color: #f1f3f4; }
                window.lunaripper-dark .lunaripper-menu-row button,
                window.lunaripper-dark .lunaripper-menu-row menubutton > button { background-color: #303238; color: #ffffff; }
                window.lunaripper-dark button.suggested-action { background-color: #245b9e; background-image: none; color: #ffffff; }
                window.lunaripper-dark button:disabled { color: #a9adb4; }

                /* LunaRipper 0.3.6 -- polished midnight-blue visual system */
                window.lunaripper-dark { background-color: #0b1424; color: #eaf2ff; }
                window.lunaripper-dark label { color: #eaf2ff; }
                window.lunaripper-dark .dim-label { color: #9aacc5; }
                window.lunaripper-dark frame { border: 1px solid #263f61; border-radius: 13px; padding: 5px; background-color: #101e33; }
                window.lunaripper-dark frame > label { color: #91c5ff; font-weight: 700; padding: 0 7px; }
                window.lunaripper-dark entry, window.lunaripper-dark dropdown,
                window.lunaripper-dark dropdown button, window.lunaripper-dark spinbutton {
                    background-color: #172841; color: #f4f8ff; border: 1px solid #385779;
                    border-radius: 8px; min-height: 34px; padding-left: 9px; padding-right: 9px;
                }
                window.lunaripper-dark entry:focus, window.lunaripper-dark dropdown:focus,
                window.lunaripper-dark spinbutton:focus { border-color: #4da5ff; }
                window.lunaripper-dark button, window.lunaripper-dark menubutton > button {
                    background-image: none; background-color: #1a2c45; color: #edf5ff;
                    border: 1px solid #385779; border-radius: 9px; padding: 7px 12px;
                    min-height: 32px; font-weight: 500;
                }
                window.lunaripper-dark button:hover, window.lunaripper-dark menubutton > button:hover {
                    background-color: #243f60; border-color: #559de7;
                }
                window.lunaripper-dark button:active { background-color: #173b68; }
                window.lunaripper-dark button.suggested-action {
                    background-image: none; background-color: #1769d2; color: #ffffff;
                    border: 1px solid #5ca9ff; border-radius: 10px; font-weight: 700;
                }
                window.lunaripper-dark button.suggested-action:hover { background-color: #2581ef; }
                window.lunaripper-dark checkbutton check { border-radius: 5px; }
                window.lunaripper-dark scrolledwindow { background-color: #0d192b; border: 1px solid #243b59; border-radius: 9px; }
                window.lunaripper-dark list, window.lunaripper-dark row,
                window.lunaripper-dark textview, window.lunaripper-dark textview text { background-color: #0d192b; color: #eaf2ff; }
                window.lunaripper-dark row { padding: 3px 5px; border-radius: 5px; }
                window.lunaripper-dark row:selected { background-color: #174f91; }
                window.lunaripper-dark progressbar trough { background-color: #1c2b40; border-radius: 6px; min-height: 8px; }
                window.lunaripper-dark progressbar progress { background-color: #3c9cff; border-radius: 6px; }
                window.lunaripper-dark scrollbar slider { background-color: #45678d; border-radius: 8px; }
                window.lunaripper-dark picture { border-radius: 9px; }

                window.lunaripper-light { background-color: #f7f7f7; color: #202124; }
                window.lunaripper-light label, window.lunaripper-light checkbutton,
                window.lunaripper-light checkbutton label, window.lunaripper-light radiobutton,
                window.lunaripper-light radiobutton label, window.lunaripper-light frame,
                window.lunaripper-light frame > label { color: #202124; }
                window.lunaripper-light entry, window.lunaripper-light spinbutton,
                window.lunaripper-light dropdown, window.lunaripper-light dropdown button,
                window.lunaripper-light button, window.lunaripper-light menubutton > button {
                    background-color: #ffffff; background-image: none; color: #202124;
                    border-color: #a6a8ad; text-shadow: none; box-shadow: none;
                }
                window.lunaripper-light entry text { color: #202124; }
                window.lunaripper-light entry placeholder { color: #666a70; }
                window.lunaripper-light list, window.lunaripper-light row,
                window.lunaripper-light scrolledwindow, window.lunaripper-light textview,
                window.lunaripper-light textview text { background-color: #ffffff; color: #202124; }
                window.lunaripper-light .lunaripper-menu-row button,
                window.lunaripper-light .lunaripper-menu-row menubutton > button { background-color: #eeeeef; color: #202124; }
                window.lunaripper-light button.suggested-action { background-color: #d8e9ff; background-image: none; color: #12385f; }
                window.lunaripper-light button:disabled { color: #777b82; }
            """)
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self._css_provider = provider
        settings = Gtk.Settings.get_default()
        if settings:
            try:
                settings.set_property('gtk-application-prefer-dark-theme', self.dark_theme)
            except (TypeError, AttributeError):
                pass


    def tr(self, text):
        return TRANSLATIONS.get(self.language, {}).get(text, text)

    def refresh_devices(self):
        devices = sorted(set(glob.glob('/dev/sr[0-9]*')))
        self.devices = [d for d in devices if Path(d).exists()]
        if self.device not in self.devices:
            self.device = self.devices[0] if self.devices else None

    def device_description(self, device):
        if not device:
            return self.tr('Kein optisches Laufwerk gefunden')
        props = {}
        try:
            result = run_command(['udevadm', 'info', '--query=property', f'--name={device}'], timeout=4)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if '=' in line:
                        k, v = line.split('=', 1); props[k] = v
        except Exception:
            pass
        kinds = []
        if props.get('ID_CDROM') == '1': kinds.append('CD')
        if props.get('ID_CDROM_DVD') == '1': kinds.append('DVD')
        if props.get('ID_CDROM_BD') == '1': kinds.append('Blu-ray')
        suffix = '/'.join(kinds) if kinds else self.tr('optisches Laufwerk')
        return f'{device} ({suffix})'

    def do_activate(self):
        if not hasattr(self, 'window'):
            self.build_ui()
        self.window.present()

    def build_ui(self):
        self.window = Gtk.ApplicationWindow(application=self, title=f'LunaRipper {APP_VERSION}')
        self.window.set_default_size(960, 690)
        self.window.set_size_request(800, 580)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(10); outer.set_margin_bottom(10); outer.set_margin_start(12); outer.set_margin_end(12)
        self.window.set_child(outer)
        self.apply_theme()

        # A genuine GTK 4 menu bar (not a row of menu-like buttons).
        menubar_model = Gio.Menu()

        file_menu = Gio.Menu()
        file_menu.append('Beenden' if self.language == 'de' else 'Quit', 'win.quit')
        menubar_model.append_submenu('Datei' if self.language == 'de' else 'File', file_menu)

        settings_menu = Gio.Menu()
        language_menu = Gio.Menu()
        language_menu.append('Deutsch', 'win.set-language-de')
        language_menu.append('English', 'win.set-language-en')
        settings_menu.append_submenu('Sprache' if self.language == 'de' else 'Language', language_menu)

        theme_menu = Gio.Menu()
        theme_menu.append('Dunkel' if self.language == 'de' else 'Dark', 'win.theme-dark')
        theme_menu.append('Hell' if self.language == 'de' else 'Light', 'win.theme-light')
        settings_menu.append_submenu('Design' if self.language == 'de' else 'Theme', theme_menu)
        settings_menu.append('CDDB bearbeiten…' if self.language == 'de' else 'CD database settings…', 'win.cddb-settings')
        settings_menu.append('Lesefehler …' if self.language == 'de' else 'Read errors…', 'win.read-error-settings')
        menubar_model.append_submenu('Einstellungen' if self.language == 'de' else 'Settings', settings_menu)

        help_menu = Gio.Menu()
        help_menu.append('Anleitung' if self.language == 'de' else 'User guide', 'win.help')
        menubar_model.append_submenu('Hilfe' if self.language == 'de' else 'Help', help_menu)

        about_menu = Gio.Menu()
        about_menu.append('Info' if self.language == 'de' else 'About', 'win.about')
        menubar_model.append_submenu('Info' if self.language == 'de' else 'About', about_menu)

        menubar = Gtk.PopoverMenuBar.new_from_model(menubar_model)
        outer.append(menubar)

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', lambda *_: self.quit())
        self.window.add_action(quit_action)

        lang_de_action = Gio.SimpleAction.new('set-language-de', None)
        lang_de_action.connect('activate', lambda action, parameter: self.set_language('de'))
        self.window.add_action(lang_de_action)
        lang_en_action = Gio.SimpleAction.new('set-language-en', None)
        lang_en_action.connect('activate', lambda action, parameter: self.set_language('en'))
        self.window.add_action(lang_en_action)

        dark_action = Gio.SimpleAction.new('theme-dark', None)
        dark_action.connect('activate', lambda action, parameter: self.set_theme(True))
        self.window.add_action(dark_action)
        light_action = Gio.SimpleAction.new('theme-light', None)
        light_action.connect('activate', lambda action, parameter: self.set_theme(False))
        self.window.add_action(light_action)

        cddb_action = Gio.SimpleAction.new('cddb-settings', None)
        cddb_action.connect('activate', self.on_cddb_settings)
        self.window.add_action(cddb_action)
        read_error_action = Gio.SimpleAction.new('read-error-settings', None)
        read_error_action.connect('activate', self.on_read_error_settings)
        self.window.add_action(read_error_action)

        # Connect menu items directly to their callbacks; each opens a modal dialog.
        help_action = Gio.SimpleAction.new('help', None)
        help_action.connect('activate', self.on_help)
        self.window.add_action(help_action)
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about)
        self.window.add_action(about_action)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        titlebox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label='🌙 LunaRipper')
        title.add_css_class('title-1'); title.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label=self.tr('Audio-CDs auslesen · Metadaten · Cover · MP3 · M4A · OGG · WAV'))
        subtitle.add_css_class('dim-label'); subtitle.set_halign(Gtk.Align.START)
        titlebox.append(title); titlebox.append(subtitle); header.append(titlebox)
        header.append(Gtk.Box(hexpand=True))
        outer.append(header)

        disc_frame = Gtk.Frame(label=self.tr('Audio-CD'))
        disc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        disc_box.set_margin_top(10); disc_box.set_margin_bottom(10); disc_box.set_margin_start(10); disc_box.set_margin_end(10)
        self.device_dropdown = Gtk.DropDown.new_from_strings([self.device_description(d) for d in self.devices] or [self.tr('Kein optisches Laufwerk gefunden')])
        if self.device in self.devices: self.device_dropdown.set_selected(self.devices.index(self.device))
        self.device_dropdown.connect('notify::selected', self.on_device_changed)
        disc_box.append(self.device_dropdown)
        self.refresh_button = Gtk.Button(label=self.tr('Laufwerk suchen'))
        self.refresh_button.connect('clicked', self.on_refresh_devices)
        disc_box.append(self.refresh_button)
        self.scan_button = Gtk.Button(label=self.tr('CD einlesen'))
        self.scan_button.connect('clicked', self.on_scan)
        disc_box.append(self.scan_button)
        self.eject_button = Gtk.Button(label=self.tr('CD auswerfen'))
        self.eject_button.connect('clicked', self.on_eject_disc)
        disc_box.append(self.eject_button)
        disc_frame.set_child(disc_box); outer.append(disc_frame)

        metadata_frame = Gtk.Frame(label=self.tr('Albumdaten'))
        meta = Gtk.Grid(column_spacing=10, row_spacing=8)
        meta.set_margin_top(10); meta.set_margin_bottom(10); meta.set_margin_start(10); meta.set_margin_end(10)
        for row, label in enumerate(('Interpret', 'Albumtitel', 'Jahr')):
            lab = Gtk.Label(label=self.tr(label)); lab.set_halign(Gtk.Align.END)
            meta.attach(lab, 0, row, 1, 1)
        self.artist_entry = Gtk.Entry(); self.artist_entry.set_placeholder_text(self.tr('Interpret oder Künstler'))
        self.album_entry = Gtk.Entry(); self.album_entry.set_placeholder_text(self.tr('Albumtitel'))
        self.year_entry = Gtk.Entry(); self.year_entry.set_placeholder_text(self.tr('z. B. 1985')); self.year_entry.set_max_length(4)
        meta.attach(self.artist_entry, 1, 0, 1, 1); meta.attach(self.album_entry, 1, 1, 1, 1); meta.attach(self.year_entry, 1, 2, 1, 1)
        self.lookup_button = Gtk.Button(label=self.tr('Daten & Cover suchen'))
        self.lookup_button.connect('clicked', self.on_lookup)
        meta.attach(self.lookup_button, 2, 0, 1, 2)
        self.cover_label = Gtk.Label(label=self.tr('Kein Cover ausgewählt'))
        self.cover_label.add_css_class('dim-label'); self.cover_label.set_halign(Gtk.Align.START)
        meta.attach(self.cover_label, 2, 2, 1, 1)
        cover_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.online_cover_button = Gtk.Button(label='Online-Cover auswählen')
        self.online_cover_button.connect('clicked', self.on_choose_online_cover)
        self.local_cover_button = Gtk.Button(label='Eigenes Bild laden…')
        self.local_cover_button.connect('clicked', self.on_choose_local_cover)
        self.no_cover_button = Gtk.Button(label='Ohne Cover')
        self.no_cover_button.connect('clicked', self.on_clear_cover)
        cover_buttons.append(self.online_cover_button); cover_buttons.append(self.local_cover_button); cover_buttons.append(self.no_cover_button)
        meta.attach(cover_buttons, 0, 3, 3, 1)
        self.cover_preview = Gtk.Picture()
        self.cover_preview.set_size_request(120, 120)
        self.cover_preview.set_can_shrink(True)
        self.cover_preview.set_content_fit(Gtk.ContentFit.CONTAIN)
        meta.attach(self.cover_preview, 3, 0, 1, 3)
        metadata_frame.set_child(meta); outer.append(metadata_frame)

        tracks_frame = Gtk.Frame(label=self.tr('Titel auswählen'))
        tracks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tracks_box.set_margin_top(8); tracks_box.set_margin_bottom(8); tracks_box.set_margin_start(8); tracks_box.set_margin_end(8)
        self.track_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.track_list.append(Gtk.Label(label=self.tr('Lies zuerst eine Audio-CD ein.')))
        scroller = Gtk.ScrolledWindow(); scroller.set_vexpand(True); scroller.set_min_content_height(90); scroller.set_child(self.track_list)
        tracks_box.append(scroller)
        selection_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.select_all_button = Gtk.Button(label=self.tr('Alle auswählen')); self.select_all_button.connect('clicked', lambda *_: self.set_all_tracks(True))
        self.select_none_button = Gtk.Button(label=self.tr('Keine auswählen')); self.select_none_button.connect('clicked', lambda *_: self.set_all_tracks(False))
        selection_row.append(self.select_all_button); selection_row.append(self.select_none_button)
        tracks_box.append(selection_row); tracks_frame.set_child(tracks_box); outer.append(tracks_frame)

        folder_frame = Gtk.Frame(label=self.tr('Speicherort'))
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        folder_box.set_margin_top(10); folder_box.set_margin_bottom(10); folder_box.set_margin_start(10); folder_box.set_margin_end(10)
        self.folder_entry = Gtk.Entry(); self.folder_entry.set_text(str(self.music_dir)); self.folder_entry.set_hexpand(True)
        self.folder_entry.connect('changed', self.on_folder_entry_changed)
        self.browse_button = Gtk.Button(label=self.tr('Durchsuchen …')); self.browse_button.connect('clicked', self.on_browse)
        folder_box.append(self.folder_entry); folder_box.append(self.browse_button); folder_frame.set_child(folder_box); outer.append(folder_frame)
        self.folder_hint = Gtk.Label(label=self.tr('Im Zielordner entsteht genau ein Albumordner: „Interpret - Albumtitel“.'))
        self.folder_hint.add_css_class('dim-label'); self.folder_hint.set_halign(Gtk.Align.START); outer.append(self.folder_hint)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.quality = Gtk.DropDown.new_from_strings(['320 kbit/s', '256 kbit/s', '192 kbit/s'])
        self.quality.set_selected(self.quality_index)
        self.quality.connect('notify::selected', self.on_quality_changed)
        bottom.append(Gtk.Label(label=self.tr('MP3-Qualität:'))); bottom.append(self.quality)
        bottom.append(Gtk.Label(label='Ausgabe:' if self.language == 'de' else 'Output:'))
        self.output_formats = ['mp3', 'ogg', 'm4a', 'wav', 'ogg_wav', 'mp3_wav', 'm4a_wav', 'mp3_ogg', 'ogg_m4a', 'mp3_m4a', 'mp3_wav_ogg', 'ogg_wav_m4a', 'mp3_wav_m4a', 'mp3_ogg_m4a', 'mp3_ogg_wav_m4a']
        self.output_dropdown = Gtk.DropDown.new_from_strings(['MP3', 'OGG', 'M4A', 'WAV', 'OGG + WAV', 'MP3 + WAV', 'M4A + WAV', 'MP3 + OGG', 'OGG + M4A', 'MP3 + M4A', 'MP3 + WAV + OGG', 'OGG + WAV + M4A', 'MP3 + WAV + M4A', 'MP3 + OGG + M4A', 'MP3 + OGG + WAV + M4A'])
        self.output_dropdown.set_selected(self.output_formats.index(self.output_format) if self.output_format in self.output_formats else 0)
        self.output_dropdown.connect('notify::selected', self.on_output_format_changed)
        bottom.append(self.output_dropdown)
        self.m3u_checkbox = Gtk.CheckButton(label=self.tr('M3U-Playlist erstellen'))
        self.m3u_checkbox.set_active(self.create_m3u)
        self.m3u_checkbox.connect('toggled', self.on_m3u_toggled)
        bottom.append(self.m3u_checkbox)
        self.progress = Gtk.ProgressBar(); self.progress.set_hexpand(True); bottom.append(self.progress)
        self.rip_button = Gtk.Button(label=self.tr('💿 Ausgewählte Titel rippen'))
        self.rip_button.add_css_class('suggested-action'); self.rip_button.connect('clicked', self.on_rip)
        self.cancel_button = Gtk.Button(label='Abbrechen' if self.language == 'de' else 'Cancel')
        self.cancel_button.set_sensitive(False)
        self.cancel_button.connect('clicked', self.on_cancel_rip)
        bottom.append(self.rip_button); bottom.append(self.cancel_button); outer.append(bottom)
        self.status = Gtk.Label(label=self.tr('Bereit.')); self.status.set_halign(Gtk.Align.START); self.status.set_wrap(True); outer.append(self.status)

        self.window.set_default_widget(self.scan_button)

    def on_cddb_settings(self, *_args):
        """Configure CD metadata provider and CDDB-compatible server."""
        dialog = Gtk.Window(
            title="CDDB-Einstellungen" if self.language == "de" else "CD database settings",
            transient_for=self.window, modal=True
        )
        dialog.set_default_size(600, 520)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18); box.set_margin_bottom(18)
        box.set_margin_start(20); box.set_margin_end(20)

        heading = Gtk.Label(label="CD-Datenbank konfigurieren" if self.language == "de" else "Configure CD metadata")
        heading.add_css_class("title-2"); heading.set_halign(Gtk.Align.START)
        box.append(heading)

        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        grid.set_hexpand(True)
        def add_row(row, label_de, label_en, widget):
            lab = Gtk.Label(label=label_de if self.language == "de" else label_en)
            lab.set_halign(Gtk.Align.END)
            widget.set_hexpand(True)
            grid.attach(lab, 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)

        provider = Gtk.DropDown.new_from_strings([
            "Freac CDDB", "dBpoweramp CDDB"
        ])
        provider.set_selected({"freac": 0, "dbpoweramp": 1}.get(self.cddb_provider, 1))
        add_row(0, "Anbieter:", "Provider:", provider)

        defaults = {
            0: ("freedb.freac.org", "/~cddb/cddb.cgi", "80"),
            1: ("freedb.dbpoweramp.com", "/~cddb/cddb.cgi", "80"),
        }
        server = Gtk.Entry(); server.set_text(self.cddb_server)
        add_row(1, "Server:", "Server:", server)
        endpoint = Gtk.Entry(); endpoint.set_text(self.cddb_path)
        add_row(2, "CGI-Pfad:", "CGI path:", endpoint)
        port = Gtk.Entry(); port.set_text(self.cddb_port)
        add_row(3, "Port (leer = Standard):", "Port (blank = default):", port)
        email = Gtk.Entry(); email.set_text(self.cddb_email)
        email.set_placeholder_text("name@example.org")
        add_row(4, "Kontakt-E-Mail:", "Contact email:", email)

        # Changing provider updates the visible endpoint fields immediately.
        # Do not silently leave a dBpoweramp endpoint selected for another provider.
        previous_provider = {"freac": 0, "dbpoweramp": 1}.get(self.cddb_provider, 1)
        def provider_changed(*_args):
            idx = provider.get_selected()
            if idx == previous_provider:
                return
            host, path, default_port = defaults.get(idx, defaults[0])
            server.set_text(host)
            endpoint.set_text(path)
            port.set_text(default_port)
        provider.connect("notify::selected", provider_changed)
        box.append(grid)

        auto_check = Gtk.CheckButton(
            label="CD beim Einlesen automatisch erkennen" if self.language == "de"
            else "Identify the CD automatically when reading it"
        )
        auto_check.set_active(self.auto_cddb)
        box.append(auto_check)

        hint = Gtk.Label(
            label=("Es bleiben die beiden CDDB-kompatiblen Anbieter Freac und dBpoweramp verfügbar.")
            if self.language == "de" else
            ("The two remaining CDDB-compatible providers are Freac and dBpoweramp.")
        )
        hint.set_wrap(True); hint.set_xalign(0); hint.add_css_class("dim-label")
        box.append(hint)

        status = Gtk.Label(label="")
        status.set_wrap(True); status.set_xalign(0)
        box.append(status)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Abbrechen" if self.language == "de" else "Cancel")
        cancel.connect("clicked", lambda *_: dialog.close())
        save = Gtk.Button(label="Speichern" if self.language == "de" else "Save")
        save.add_css_class("suggested-action")

        def collect_settings():
            selected_provider = {0: "freac", 1: "dbpoweramp"}.get(provider.get_selected(), "dbpoweramp")
            server_value = server.get_text().strip()
            path_value = endpoint.get_text().strip()
            port_value = port.get_text().strip()
            email_value = email.get_text().strip()
            if selected_provider in ("freac", "dbpoweramp"):
                if not server_value or not path_value.startswith("/"):
                    raise ValueError("Server und CGI-Pfad müssen gültig sein." if self.language == "de" else "Server and CGI path are required.")
                if port_value and (not port_value.isdigit() or not (1 <= int(port_value) <= 65535)):
                    raise ValueError("Port muss zwischen 1 und 65535 liegen." if self.language == "de" else "Port must be between 1 and 65535.")
            self.cddb_provider = selected_provider
            defaults = {
                "freac": ("freedb.freac.org", "/~cddb/cddb.cgi", "80"),
                "dbpoweramp": ("freedb.dbpoweramp.com", "/~cddb/cddb.cgi", "80"),
            }
            default_server, default_path, default_port = defaults[selected_provider]
            if not server_value or server_value in ("gnudb.gnudb.org", "musicbrainz.org") or (server_value == "freedb.dbpoweramp.com" and selected_provider == "freac") or (server_value == "freedb.freac.org" and selected_provider == "dbpoweramp"):
                self.cddb_server = default_server
                server.set_text(default_server)
            else:
                self.cddb_server = server_value
            self.cddb_path = path_value or default_path
            if selected_provider in ("freac", "dbpoweramp") and port_value in ("", "80"):
                self.cddb_port = default_port
                port.set_text(default_port)
            self.cddb_port = port_value or "80"
            self.cddb_email = email_value
            self.auto_cddb = auto_check.get_active()
            self.save_settings()

        def save_clicked(*_args):
            try:
                collect_settings()
            except ValueError as exc:
                status.set_text(str(exc)); return
            self.set_status("CDDB-Einstellungen gespeichert." if self.language == "de" else "CD database settings saved.")
            dialog.close()

        def test_clicked(*_args):
            try:
                collect_settings()
            except ValueError as exc:
                status.set_text(str(exc)); return
            status.set_text("Verbindung wird getestet …" if self.language == "de" else "Testing connection…")
            threading.Thread(target=self.cddb_test_worker, args=(status,), daemon=True).start()

        test = Gtk.Button(label="Verbindung testen" if self.language == "de" else "Test connection")
        test.connect("clicked", test_clicked)
        buttons.append(cancel); buttons.append(test); buttons.append(save)
        box.append(buttons)
        dialog.set_child(box)
        dialog.present()

    def on_read_error_settings(self, *_args):
        """Configure retries and optional best-effort reading for damaged audio CDs."""
        de = self.language == "de"
        dialog = Gtk.Window(
            title="Lesefehler-Einstellungen" if de else "Read error settings",
            transient_for=self.window, modal=True
        )
        dialog.set_default_size(520, 330)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(18); box.set_margin_bottom(18)
        box.set_margin_start(20); box.set_margin_end(20)
        heading = Gtk.Label(label="Umgang mit Lesefehlern" if de else "Handling read errors")
        heading.add_css_class("title-2"); heading.set_halign(Gtk.Align.START)
        box.append(heading)

        retries_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        retries_label = Gtk.Label(label="Zusätzliche Leseversuche:" if de else "Additional read attempts:")
        retries_label.set_halign(Gtk.Align.START); retries_label.set_hexpand(True)
        retries = Gtk.DropDown.new_from_strings(["0", "1", "2", "3", "5"])
        retries.set_selected({0: 0, 1: 1, 2: 2, 3: 3, 5: 4}.get(self.read_retries, 3))
        retries_row.append(retries_label); retries_row.append(retries); box.append(retries_row)

        ignore = Gtk.CheckButton(label=("Lesefehler ignorieren und notfalls mit weniger strenger Fehlerprüfung fortfahren"
                                       if de else "Ignore read errors and continue with less strict error checking if needed"))
        ignore.set_active(self.ignore_read_errors)
        box.append(ignore)
        hint = Gtk.Label(label=(
            "Standardmäßig bleibt das sichere Auslesen aktiv. Wenn diese Option eingeschaltet ist, versucht LunaRipper nach erfolglosen normalen Leseversuchen einen bestmöglichen Rettungsversuch. Die Datei kann dann beschädigte oder fehlende Audiodaten enthalten. Ein nicht reagierendes Laufwerk kann trotzdem einen Abbruch erfordern."
            if de else
            "Normal, error-checked reading remains the default. When enabled, LunaRipper makes a best-effort recovery attempt after normal reads fail. The resulting file may contain damaged or missing audio. A drive that stops responding may still require aborting the operation."
        ))
        hint.set_wrap(True); hint.set_xalign(0); hint.add_css_class("dim-label"); box.append(hint)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Abbrechen" if de else "Cancel")
        cancel.connect("clicked", lambda *_: dialog.close())
        save = Gtk.Button(label="Speichern" if de else "Save")
        save.add_css_class("suggested-action")
        def save_clicked(*_args):
            self.read_retries = [0, 1, 2, 3, 5][retries.get_selected()]
            self.ignore_read_errors = ignore.get_active()
            self.save_settings()
            self.set_status("Lesefehler-Einstellungen gespeichert." if de else "Read error settings saved.")
            dialog.close()
        save.connect("clicked", save_clicked)
        buttons.append(cancel); buttons.append(save); box.append(buttons)
        dialog.set_child(box); dialog.present()

    def cddb_test_worker(self, status_label):
        try:
            if self.cddb_provider == "musicbrainz":
                url = "https://musicbrainz.org/ws/2/"
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            else:
                scheme = "https" if self.cddb_port == "443" else "http"
                port_suffix = "" if (scheme == "https" and self.cddb_port == "443") or (scheme == "http" and self.cddb_port == "80") else f":{self.cddb_port}"
                url = f"{scheme}://{self.cddb_server}{port_suffix}{self.cddb_path}?" + urllib.parse.urlencode({
                    "cmd": "stat",
                    "hello": f"{self.cddb_email.strip().split('@')[0]} {self.cddb_email.strip().split('@')[-1]} LunaRipper {APP_VERSION}" if "@" in self.cddb_email else f"lunaripper localhost LunaRipper {APP_VERSION}",
                    "proto": "6"
                })
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=12) as response:
                response.read(512)
            message = "Verbindung erfolgreich." if self.language == "de" else "Connection successful."
        except Exception as exc:
            message = (f"Verbindung fehlgeschlagen: {exc}" if self.language == "de"
                       else f"Connection failed: {exc}")
        GLib.idle_add(status_label.set_text, message)

    def show_text_dialog(self, title, heading, body, width=600, height=480, sections=None):
        """Show a structured GTK4 information window without preselected text."""
        dialog = Gtk.Window(title=title, transient_for=self.window, modal=True)
        dialog.set_default_size(width, height)
        dialog.set_resizable(True)

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer_box.set_margin_top(20)
        outer_box.set_margin_bottom(18)
        outer_box.set_margin_start(22)
        outer_box.set_margin_end(22)

        title_label = Gtk.Label(label=heading)
        title_label.add_css_class("title-1")
        title_label.set_halign(Gtk.Align.START)
        outer_box.append(title_label)

        if sections:
            for section_title, section_body in sections:
                section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                section_label = Gtk.Label(label=section_title)
                section_label.add_css_class("heading")
                section_label.set_halign(Gtk.Align.START)
                section_box.append(section_label)

                body_label = Gtk.Label(label=section_body)
                body_label.set_wrap(True)
                body_label.set_selectable(False)
                body_label.set_halign(Gtk.Align.FILL)
                body_label.set_xalign(0)
                body_label.set_yalign(0)
                section_box.append(body_label)
                outer_box.append(section_box)
        else:
            body_label = Gtk.Label(label=body)
            body_label.set_wrap(True)
            body_label.set_selectable(False)
            body_label.set_halign(Gtk.Align.FILL)
            body_label.set_xalign(0)
            body_label.set_yalign(0)
            outer_box.append(body_label)

        close_button = Gtk.Button(label="Schließen" if self.language == "de" else "Close")
        close_button.set_halign(Gtk.Align.END)
        close_button.connect("clicked", lambda *_: dialog.close())
        outer_box.append(close_button)
        dialog.set_child(outer_box)
        dialog.present()
        return dialog

    def on_help(self, *_args):
        if self.language == "en":
            title = "LunaRipper – User guide"
            sections = [
                ("1. Read the CD", "Insert an audio CD, choose the optical drive and click “Read disc”. The track list will appear below."),
                ("2. Find album information", "Enter artist and album title, then click “Find metadata & cover”. An internet connection is required."),
                ("3. Choose the destination", "Select the music folder with “Browse…”. LunaRipper creates one album folder named “Artist - Album title”."),
                ("4. Rip tracks to MP3", "Choose the MP3 bitrate, select the tracks you want and click “Rip selected tracks”."),
                ("Settings", "Language, theme, destination folder, drive and MP3 quality are saved in ~/.config/lunaripper/settings.json."),
            ]
        else:
            title = "LunaRipper – Anleitung"
            sections = [
                ("1. CD einlesen", "Lege eine Audio-CD ein, wähle das optische Laufwerk und klicke auf „CD einlesen“. Danach erscheint die Titelliste."),
                ("2. Albumdaten suchen", "Gib Interpret und Albumtitel ein und klicke auf „Daten & Cover suchen“. Dafür wird eine Internetverbindung benötigt."),
                ("3. Speicherort wählen", "Wähle über „Durchsuchen …“ deinen Musikordner. LunaRipper legt darin genau einen Albumordner „Interpret - Albumtitel“ an."),
                ("4. Titel als MP3 rippen", "Wähle die MP3-Qualität, markiere die gewünschten Titel und klicke auf „Ausgewählte Titel rippen“."),
                ("Einstellungen", "Sprache, Design, Speicherort, Laufwerk und MP3-Qualität stehen in ~/.config/lunaripper/settings.json."),
            ]
        return self.show_text_dialog(title, title, "", width=640, height=560, sections=sections)

    def on_about(self, *_args):
        if self.language == "en":
            title = "LunaRipper – About"
            sections = [
                ("Application", "LunaRipper"),
                ("Version", APP_VERSION),
                ("Publisher", "Goldisoft 2026"),
                ("Purpose", "Audio CD ripping with metadata and cover support."),
            ]
        else:
            title = "LunaRipper – Info"
            sections = [
                ("Programm", "LunaRipper"),
                ("Version", APP_VERSION),
                ("Herausgeber", "Goldisoft 2026"),
                ("Funktion", "Audio-CD-Ripper mit Metadaten- und Cover-Unterstützung."),
            ]
        return self.show_text_dialog(title, title, "", width=460, height=330, sections=sections)

    def set_language(self, language):
        if language not in ("de", "en"):
            return
        if language == self.language:
            return
        self.language = language
        self.save_settings()
        old_window = self.window
        old_window.destroy()
        self.build_ui()
        self.window.present()

    def set_theme(self, dark):
        self.dark_theme = bool(dark)
        self.apply_theme()
        self.save_settings()

    def on_language_changed(self, dropdown, _pspec):
        new_language = 'de' if dropdown.get_selected() == 0 else 'en'
        if new_language == self.language: return
        self.language = new_language
        self.save_settings()
        old = self.window
        old.destroy()
        self.build_ui()
        self.window.present()

    def on_dark_changed(self, switch, _pspec):
        self.dark_theme = switch.get_active()
        self.apply_theme()
        self.save_settings()

    def on_folder_entry_changed(self, entry):
        value = entry.get_text().strip()
        if value:
            self.music_dir = Path(value).expanduser()
            self.save_settings()

    def on_quality_changed(self, dropdown, _pspec):
        self.quality_index = dropdown.get_selected()
        self.save_settings()

    def on_device_changed(self, dropdown, _pspec):
        idx = dropdown.get_selected()
        if idx < len(self.devices):
            self.device = self.devices[idx]
            self.save_settings()

    def on_eject_disc(self, *_):
        """Eject the currently selected optical drive tray."""
        if not self.device or self.device not in self.devices:
            self.set_status(self.tr('Kein optisches Laufwerk gefunden.'))
            return
        try:
            result = subprocess.run(['eject', self.device], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.set_status(self.tr('CD-Laufwerk wurde ausgeworfen.'))
            else:
                detail = (result.stderr or result.stdout or '').strip()
                message = self.tr('CD konnte nicht ausgeworfen werden.')
                if detail:
                    message += ' ' + detail
                self.set_status(message)
        except FileNotFoundError:
            self.set_status(self.tr('Das Programm „eject“ fehlt. Bitte das Paket eject installieren.'))
        except subprocess.TimeoutExpired:
            self.set_status(self.tr('Zeitüberschreitung beim Auswerfen der CD.'))
        except Exception as exc:
            self.set_status(self.tr('CD konnte nicht ausgeworfen werden.') + ' ' + str(exc))

    def on_refresh_devices(self, *_):
        self.refresh_devices()
        model = Gtk.StringList.new([self.device_description(d) for d in self.devices] or [self.tr('Kein optisches Laufwerk gefunden')])
        self.device_dropdown.set_model(model)
        if self.device in self.devices: self.device_dropdown.set_selected(self.devices.index(self.device))
        self.set_status(self.tr('Laufwerkssuche abgeschlossen.') if self.devices else self.tr('Kein optisches Laufwerk gefunden.'))

    def set_status(self, message):
        if self.language == 'en':
            replacements = [
                ('Fehler beim Einlesen der CD:', 'Error reading the disc:'),
                ('Fehler:', 'Error:'),
                ('Metadatensuche fehlgeschlagen:', 'Metadata search failed:'),
                ('MP3 erstellt, aber ID3-Tags konnten nicht vollständig geschrieben werden:', 'MP3 created, but ID3 tags could not be fully written:'),
                ('Übersprungen, Datei existiert bereits:', 'Skipped, file already exists:'),
                ('Rippe Titel', 'Ripping track'),
                ('Fertig! Dateien gespeichert in:', 'Done! Files saved to:'),
                (' Titel erkannt.', ' tracks detected.'),
            ]
            for old, new in replacements:
                message = message.replace(old, new)
            message = TRANSLATIONS['en'].get(message, message)
        GLib.idle_add(self.status.set_text, message)

    def on_browse(self, *_):
        dialog = Gtk.FileChooserNative.new(self.tr('Speicherordner auswählen'), self.window, Gtk.FileChooserAction.SELECT_FOLDER, self.tr('Auswählen'), self.tr('Abbrechen'))
        current = Path(self.folder_entry.get_text()).expanduser()
        if current.is_dir():
            try: dialog.set_current_folder(Gio.File.new_for_path(str(current)))
            except Exception: pass
        dialog.connect('response', self.on_folder_chosen)
        dialog.show()

    def on_folder_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            f = dialog.get_file()
            if f and f.get_path():
                self.folder_entry.set_text(f.get_path())
                self.music_dir = Path(f.get_path())
                self.save_settings()
        dialog.destroy()

    def on_scan(self, *_):
        if self.ripping: return
        self.scan_button.set_sensitive(False); self.status.set_text('Audio-CD wird untersucht …')
        threading.Thread(target=self.scan_disc_worker, daemon=True).start()

    def scan_disc_worker(self):
        device = self.device
        if not device or not Path(device).exists():
            self.set_status(self.tr('Kein optisches Laufwerk gefunden. Bitte Laufwerk suchen.'))
            GLib.idle_add(self.scan_button.set_sensitive, True); return
        try:
            result = subprocess.run(['cdparanoia', '-d', device, '-Q'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25)
            output = (result.stdout or '') + '\n' + (result.stderr or '')
            # cdparanoia prints TOC lines such as: 1. 00:00:00 00:03:45 audio
            found = []
            for line in output.splitlines():
                # cdparanoia versions vary in the TOC display format. Track rows begin with "N.".
                m = re.match(r'^\s*(\d+)\.\s+', line)
                if m:
                    number = int(m.group(1))
                    if not any(t['number'] == number for t in found):
                        times = re.findall(r'\[(\d{2}:\d{2}\.\d{2})\]', line)
                        duration = times[0] if times else '--:--.--'
                        begin = times[1] if len(times) > 1 else '--:--.--'
                        found.append({'number': number, 'duration': duration, 'start': begin, 'end': begin, 'title': f'Titel {number:02d}'})
            if not found:
                self.set_status('Keine Audio-CD-Titel erkannt. Bitte CD einlegen und Laufwerk prüfen. Details: ' + (output.strip()[-250:] or 'keine Ausgabe'))
                GLib.idle_add(self.scan_button.set_sensitive, True); return
            self.tracks = found
            # Automatic disc identification can be switched on/off in Settings.
            if self.auto_cddb and shutil_which('cd-discid'):
                try:
                    disc_result = subprocess.run(['cd-discid', device], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                    parts = disc_result.stdout.strip().split()
                    if disc_result.returncode == 0 and len(parts) >= 4:
                        self.disc_id = parts[0]
                        if self.cddb_provider in ("gnudb", "freac", "dbpoweramp"):
                            self.lookup_gnudb(parts, found)
                        else:
                            self.lookup_discid(found, self.disc_id)
                except Exception:
                    pass
            GLib.idle_add(self.show_tracks)
            self.set_status(f'{len(found)} Titel erkannt. ' + ('CD-Daten automatisch zugeordnet.' if any(not t['title'].startswith('Titel ') for t in found) else 'Wenn die CD nicht automatisch erkannt wurde, trage Interpret und Album ein und suche Daten & Cover.'))
        except Exception as exc:
            self.set_status(f'Fehler beim Einlesen der CD: {exc}')
        finally:
            GLib.idle_add(self.scan_button.set_sensitive, True)

    def lookup_gnudb(self, discid_parts, tracks):
        """Query GNUDB using the CDDB-compatible HTTP protocol and apply its metadata."""
        try:
            # cd-discid output: discid track_count offsets... total_seconds
            discid = discid_parts[0]
            track_count = int(discid_parts[1])
            offsets = [int(value) for value in discid_parts[2:2 + track_count]]
            total_seconds = int(discid_parts[2 + track_count])
            if len(offsets) != track_count:
                return
            port = self.cddb_port or "443"
            scheme = "https" if port == "443" else "http"
            port_suffix = "" if (scheme == "https" and port == "443") or (scheme == "http" and port == "80") else f":{port}"
            base = f"{scheme}://{self.cddb_server}{port_suffix}{self.cddb_path}"
            # GNUDB requires a real contact address and a descriptive application identity.
            email = self.cddb_email.strip()
            if "@" in email:
                email_name, email_domain = email.rsplit("@", 1)
            else:
                email_name, email_domain = "lunaripper", "localhost"
            hello = f"{email_name} {email_domain} LunaRipper {APP_VERSION}"
            query_command = "cddb query " + " ".join([discid, str(track_count), *map(str, offsets), str(total_seconds)])
            query_url = base + "?" + urllib.parse.urlencode({"cmd": query_command, "hello": hello, "proto": "6"})
            req = urllib.request.Request(query_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as response:
                query_text = response.read().decode("utf-8", errors="replace")
            # CDDB protocol replies can return a direct match (200) or a
            # multiline list (210/211). In multiline replies the entries do
            # NOT repeat the status code, so parse those rows separately.
            match = None
            lines = query_text.replace("\r", "").splitlines()
            for line in lines:
                direct = re.match(r"^\s*200\s+([a-zA-Z0-9_-]+)\s+([0-9a-fA-F]{8})\s+(.+)$", line)
                if direct:
                    match = (direct.group(1), direct.group(2), direct.group(3).strip())
                    break
            if not match:
                multiline = any(re.match(r"^\s*(?:210|211)\b", line) for line in lines)
                if multiline:
                    for line in lines:
                        row = re.match(r"^\s*([a-zA-Z0-9_-]+)\s+([0-9a-fA-F]{8})\s+(.+?)\s*$", line)
                        if row and row.group(1).lower() not in ("210", "211"):
                            match = (row.group(1), row.group(2), row.group(3).strip())
                            break
            if not match:
                first_reply = next((line.strip() for line in lines if line.strip()), "Leere Serverantwort")
                GLib.idle_add(self.set_status, f"CDDB-Server antwortet: {first_reply}")
                return
            category, gnucdid, _display_title = match
            read_command = f"cddb read {category} {gnucdid}"
            read_url = base + "?" + urllib.parse.urlencode({"cmd": read_command, "hello": hello, "proto": "6"})
            req = urllib.request.Request(read_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as response:
                entry = response.read().decode("utf-8", errors="replace")
            fields = {}
            current_key = None
            for line in entry.splitlines():
                if line == ".":
                    break
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    fields[key] = value
                    current_key = key
                elif line[:1].isspace() and current_key:
                    fields[current_key] += line.strip()
            dtitle = fields.get("DTITLE", "")
            if " / " in dtitle:
                artist, album = dtitle.split(" / ", 1)
            else:
                artist, album = "", dtitle
            year = fields.get("DYEAR", "").strip()
            if artist:
                GLib.idle_add(self.artist_entry.set_text, artist.strip())
            if album:
                GLib.idle_add(self.album_entry.set_text, album.strip())
            if year:
                GLib.idle_add(self.year_entry.set_text, year[:4])
            # CDDB TTITLE fields are zero-based (TTITLE0 = physical track 1).
            # Resolve every title from the physical CD track number, not from
            # the current list position; this keeps names attached to the right
            # track even if the track list is filtered or reordered.
            for track in tracks:
                try:
                    cddb_index = int(track['number']) - 1
                except (KeyError, TypeError, ValueError):
                    continue
                title = fields.get(f"TTITLE{cddb_index}", "").strip()
                if title:
                    track["title"] = title
            cover_url = next((line.split(":", 1)[1].strip() for line in entry.splitlines()
                              if line.startswith("# Cover:") and "coverartarchive.org" in line), "")
            # Never embed a CDDB-supplied cover silently; ask the user to confirm it.
            if cover_url:
                try:
                    req = urllib.request.Request(cover_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=12) as response:
                        candidate_bytes = response.read()
                    self.cover_candidates = [{'id': 'CDDB', 'title': f'{album} (CDDB-Cover)', 'artist': artist, 'date': year, 'bytes': candidate_bytes}]
                    self.cover_bytes = None
                    GLib.idle_add(self.show_online_cover_choices, self.cover_candidates)
                    GLib.idle_add(self.cover_label.set_text, 'Online-Cover verfügbar – bitte auswählen')
                except Exception:
                    self.cover_bytes = None
                    GLib.idle_add(self.cover_label.set_text, 'Kein Online-Cover gefunden; eigenes Bild möglich')
            else:
                self.cover_bytes = None
                self.cover_candidates = []
                GLib.idle_add(self.cover_label.set_text, 'Kein Online-Cover gefunden; eigenes Bild möglich')
            GLib.idle_add(self.show_tracks)
            GLib.idle_add(self.set_status, f"CDDB ({self.cddb_server}): Metadaten für {len(tracks)} Titel übernommen.")
        except Exception as exc:
            GLib.idle_add(self.set_status, f"CDDB-Abfrage fehlgeschlagen ({self.cddb_server}): {exc}")

    def lookup_discid(self, tracks, disc_id):
        """Look up the inserted disc by MusicBrainz disc ID, including recording titles."""
        try:
            url = f'https://musicbrainz.org/ws/2/discid/{urllib.parse.quote(disc_id)}?' + urllib.parse.urlencode({'inc': 'artists+recordings', 'fmt': 'json'})
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            releases = data.get('releases', [])
            if not releases:
                return
            release = releases[0]
            self.release_id = release.get('id')
            release_title = release.get('title') or ''
            artist_name = ', '.join(a.get('name', '') for a in release.get('artist-credit', []) if isinstance(a, dict) and a.get('name'))
            year = (release.get('date') or '')[:4]
            media = release.get('media', [])
            release_tracks = []
            for medium in media:
                release_tracks.extend(medium.get('tracks', []))
            # Keep metadata tied to physical CD track numbers.
            # Match MusicBrainz titles by physical track number instead of
            # assuming both lists have identical ordering.
            mb_by_number = {}
            for mb_track in release_tracks:
                try:
                    mb_number = int(mb_track.get('number'))
                except (TypeError, ValueError):
                    continue
                mb_by_number.setdefault(mb_number, mb_track)
            for track in tracks:
                try:
                    mb_track = mb_by_number.get(int(track['number']))
                except (KeyError, TypeError, ValueError):
                    mb_track = None
                if not mb_track:
                    continue
                title = (mb_track.get('title') or '').strip()
                if title:
                    track['title'] = title
            if artist_name:
                GLib.idle_add(self.artist_entry.set_text, artist_name)
            if release_title:
                GLib.idle_add(self.album_entry.set_text, release_title)
            if year:
                GLib.idle_add(self.year_entry.set_text, year)
            rid = self.release_id
            if rid:
                try:
                    cover_req = urllib.request.Request(f'https://coverartarchive.org/release/{rid}/front-500', headers={'User-Agent': USER_AGENT})
                    with urllib.request.urlopen(cover_req, timeout=12) as resp:
                        candidate_bytes = resp.read()
                    candidate = {'id': rid, 'title': release_title or 'Album', 'artist': artist_name, 'date': year, 'bytes': candidate_bytes}
                    self.cover_candidates = [candidate]
                    self.cover_bytes = None
                    GLib.idle_add(self.show_online_cover_choices, self.cover_candidates)
                    GLib.idle_add(self.cover_label.set_text, 'Online-Cover verfügbar – bitte auswählen')
                except Exception:
                    self.cover_bytes = None
                    GLib.idle_add(self.cover_label.set_text, 'Kein Online-Cover gefunden; eigenes Bild möglich')
        except Exception:
            # A missing match or unavailable network must not prevent ripping.
            return

    def show_tracks(self):
        child = self.track_list.get_first_child()
        while child:
            nxt = child.get_next_sibling(); self.track_list.remove(child); child = nxt
        self.track_checks = []
        for track in self.tracks:
            check = Gtk.CheckButton(label=f"{track['number']:02d}   {track['title']}   ({track.get('duration', '--:--.--')})")
            check.set_active(True); check.track_data = track
            self.track_list.append(check); self.track_checks.append(check)
        # Drive is shown in the selector; keep its selection and show detected track count in status.
        self.set_status(f'{len(self.tracks)} Titel erkannt.')

    def set_all_tracks(self, active):
        for check in self.track_checks: check.set_active(active)

    def on_lookup(self, *_):
        artist = self.artist_entry.get_text().strip(); album = self.album_entry.get_text().strip()
        if not artist or not album:
            self.status.set_text(self.tr('Bitte Interpret und Albumtitel eintragen, damit wir Metadaten und Cover suchen können.'))
            return
        self.lookup_button.set_sensitive(False); self.status.set_text(self.tr('Suche bei MusicBrainz und Cover Art Archive …'))
        threading.Thread(target=self.lookup_worker, args=(artist, album), daemon=True).start()

    def lookup_worker(self, artist, album):
        try:
            query = f'artist:"{artist}" AND release:"{album}"'
            url = 'https://musicbrainz.org/ws/2/release/?' + urllib.parse.urlencode({'query': query, 'fmt': 'json', 'limit': 5})
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=15) as resp: data = json.loads(resp.read().decode('utf-8'))
            releases = data.get('releases', [])
            if not releases:
                self.set_status('Kein passender Eintrag gefunden. Interpret und Albumtitel bleiben wie eingegeben; du kannst trotzdem rippen.')
                return
            release = releases[0]
            rid = release.get('id'); date = (release.get('date') or '')[:4]
            title = release.get('title') or album
            artist_name = ', '.join(a.get('name', '') for a in release.get('artist-credit', []) if isinstance(a, dict) and a.get('name')) or artist
            # Gather several distinct release covers so the user can choose the correct edition.
            candidates = []
            seen = set()
            for item in releases[:5]:
                candidate_id = item.get('id')
                if not candidate_id or candidate_id in seen:
                    continue
                seen.add(candidate_id)
                candidate_cover = None
                try:
                    cover_req = urllib.request.Request(f'https://coverartarchive.org/release/{candidate_id}/front-500', headers={'User-Agent': USER_AGENT})
                    with urllib.request.urlopen(cover_req, timeout=10) as resp: candidate_cover = resp.read()
                except Exception:
                    continue
                candidate_artist = ', '.join(a.get('name', '') for a in item.get('artist-credit', []) if isinstance(a, dict) and a.get('name')) or artist
                candidate_title = item.get('title') or album
                candidate_date = (item.get('date') or '')[:4]
                candidates.append({'id': candidate_id, 'title': candidate_title, 'artist': candidate_artist, 'date': candidate_date, 'bytes': candidate_cover})
            self.release_id = rid
            self.cover_candidates = candidates
            # Don't silently accept the first image: selection is explicitly the user's choice.
            self.cover_bytes = None
            self.cover_source = 'none'
            # Cover/album lookup must never replace the CD's existing track list.
            # Search results may refer to a different edition or track ordering;
            # changing titles here made the list appear shuffled when choosing a cover.
            GLib.idle_add(self.artist_entry.set_text, artist_name)
            GLib.idle_add(self.album_entry.set_text, title)
            if date: GLib.idle_add(self.year_entry.set_text, date)
            GLib.idle_add(self.cover_label.set_text, f'{len(candidates)} Online-Cover verfügbar – bitte auswählen' if candidates else 'Kein Online-Cover gefunden; eigenes Bild möglich')
            if candidates:
                GLib.idle_add(self.show_online_cover_choices, candidates)
            self.set_status('Metadaten gefunden. Bitte kontrolliere Interpret, Album und Titelnamen vor dem Rippen.')
        except Exception as exc:
            detail = str(exc)
            if '503' in detail or '502' in detail or '504' in detail:
                detail = 'Der Online-Metadatendienst ist vorübergehend nicht erreichbar (HTTP ' + next((code for code in ('503','502','504') if code in detail), '5xx') + '). Bitte später erneut versuchen.'
            self.set_status(f'Metadatensuche fehlgeschlagen: {detail} Du kannst ein eigenes Cover laden oder ohne Cover rippen.')
        finally:
            GLib.idle_add(self.lookup_button.set_sensitive, True)

    def _set_cover(self, data, source, label):
        self.cover_bytes = data
        self.cover_source = source if data else 'none'
        self.cover_label.set_text(label if data else 'Kein Cover ausgewählt')
        if not data:
            self.cover_preview.set_paintable(None)
            return
        try:
            texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
            self.cover_preview.set_paintable(texture)
        except Exception:
            self.cover_preview.set_paintable(None)

    def on_clear_cover(self, *_):
        self._set_cover(None, 'none', 'Kein Cover ausgewählt')
        self.set_status('Cover deaktiviert. Die MP3-Dateien werden ohne Cover gespeichert.')

    def on_choose_local_cover(self, *_):
        dialog = Gtk.FileChooserNative.new('Eigenes Cover-Bild auswählen', self.window, Gtk.FileChooserAction.OPEN, 'Öffnen', 'Abbrechen')
        image_filter = Gtk.FileFilter()
        image_filter.set_name('Bilddateien (JPEG, PNG, WebP)')
        for pattern in ('*.jpg', '*.jpeg', '*.png', '*.webp', '*.JPG', '*.JPEG', '*.PNG', '*.WEBP'):
            image_filter.add_pattern(pattern)
        dialog.add_filter(image_filter)
        dialog.connect('response', self.on_local_cover_chosen)
        dialog.show()

    def on_local_cover_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            try:
                path = Path(file.get_path()) if file and file.get_path() else None
                if path and path.is_file():
                    data = path.read_bytes()
                    if not data or len(data) > 20 * 1024 * 1024:
                        raise ValueError('Bild ist leer oder größer als 20 MB.')
                    # Mutagen APIC expects the actual MIME type for embedded artwork.
                    suffix = path.suffix.lower()
                    if suffix not in ('.jpg', '.jpeg', '.png', '.webp'):
                        raise ValueError('Nicht unterstütztes Bildformat.')
                    self._set_cover(data, 'local', f'Eigenes Cover: {path.name}')
                    self.set_status(f'Eigenes Cover ausgewählt: {path.name}')
            except Exception as exc:
                self.set_status(f'Cover konnte nicht geladen werden: {exc}')
        dialog.destroy()

    def on_choose_online_cover(self, *_):
        if self.cover_candidates:
            self.show_online_cover_choices(self.cover_candidates)
        else:
            # A temporary MusicBrainz/Cover Art Archive outage should not leave this button inert.
            self.set_status('Keine Online-Cover im Speicher. Suche erneut; der Online-Dienst kann vorübergehend nicht erreichbar sein …')
            self.on_lookup()

    def show_online_cover_choices(self, candidates):
        dialog = Gtk.Dialog(title='Online-Cover auswählen', transient_for=self.window, modal=True)
        dialog.set_default_size(560, 420)
        dialog.add_button('Abbrechen', Gtk.ResponseType.CANCEL)
        dialog.add_button('Cover übernehmen', Gtk.ResponseType.ACCEPT)
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12); content.set_margin_bottom(12); content.set_margin_start(12); content.set_margin_end(12)
        intro = Gtk.Label(label='Wähle das Cover aus, das zu deiner CD-Ausgabe passt. Die Bilder stammen aus dem Cover Art Archive.')
        intro.set_wrap(True); intro.set_halign(Gtk.Align.START); content.append(intro)
        scroll = Gtk.ScrolledWindow(); scroll.set_min_content_height(260); scroll.set_vexpand(True)
        listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        group = None
        buttons = []
        for index, candidate in enumerate(candidates):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_top(4); row.set_margin_bottom(4)
            radio = Gtk.CheckButton()
            if group is None: group = radio
            else: radio.set_group(group)
            radio.set_active(index == 0)
            thumb = Gtk.Picture(); thumb.set_size_request(76, 76); thumb.set_can_shrink(True); thumb.set_content_fit(Gtk.ContentFit.CONTAIN)
            try: thumb.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(candidate['bytes'])))
            except Exception: pass
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            title_label = Gtk.Label(label=candidate['title']); title_label.set_halign(Gtk.Align.START); title_label.set_wrap(True)
            detail = ' · '.join(x for x in (candidate.get('artist'), candidate.get('date'), candidate.get('id','')[:8]) if x)
            detail_label = Gtk.Label(label=detail); detail_label.set_halign(Gtk.Align.START); detail_label.add_css_class('dim-label'); detail_label.set_wrap(True)
            text_box.append(title_label); text_box.append(detail_label)
            row.append(radio); row.append(thumb); row.append(text_box); listbox.append(row)
            buttons.append((radio, candidate))
        scroll.set_child(listbox); content.append(scroll)
        def response_cb(dlg, response):
            if response == Gtk.ResponseType.ACCEPT:
                chosen = next((candidate for radio, candidate in buttons if radio.get_active()), None)
                if chosen:
                    self._set_cover(chosen['bytes'], 'online', f"Cover ausgewählt: {chosen['title']} ({chosen.get('date') or 'Jahr unbekannt'})")
                    self.set_status('Online-Cover ausgewählt und wird in die MP3-Dateien eingebettet.')
            dlg.destroy()
        dialog.connect('response', response_cb)
        dialog.present()

    def on_output_format_changed(self, dropdown, _pspec):
        formats = ['mp3', 'ogg', 'm4a', 'wav', 'ogg_wav', 'mp3_wav', 'm4a_wav', 'mp3_ogg', 'ogg_m4a', 'mp3_m4a', 'mp3_wav_ogg', 'ogg_wav_m4a', 'mp3_wav_m4a', 'mp3_ogg_m4a', 'mp3_ogg_wav_m4a']
        index = dropdown.get_selected()
        self.output_format = formats[index] if 0 <= index < len(formats) else 'mp3'
        self.save_settings()

    def on_m3u_toggled(self, checkbox):
        self.create_m3u = checkbox.get_active()
        self.save_settings()

    def on_rip(self, *_):
        if self.ripping: return
        selected = [dict(c.track_data) for c in self.track_checks if c.get_active()]
        if not selected:
            self.status.set_text(self.tr('Bitte mindestens einen Titel auswählen.')); return
        artist = self.artist_entry.get_text().strip()
        album = self.album_entry.get_text().strip()
        if not artist: artist = 'Unbekannter Interpret'
        if not album: album = 'Unbekanntes Album'
        root_text = self.folder_entry.get_text().strip()
        if not root_text:
            self.status.set_text(self.tr('Bitte einen Speicherordner auswählen.')); return
        root = Path(root_text).expanduser()
        quality_map = {0: '320', 1: '256', 2: '192'}
        bitrate = quality_map.get(self.quality.get_selected(), '320')
        device = self.device
        if not device:
            self.status.set_text(self.tr('Kein optisches Laufwerk gefunden.')); return
        self.ripping = True
        self.cancel_requested.clear()
        self.rip_button.set_sensitive(False); self.cancel_button.set_sensitive(True)
        self.scan_button.set_sensitive(False); self.lookup_button.set_sensitive(False)
        threading.Thread(target=self.rip_worker, args=(selected, root, artist, album, self.year_entry.get_text().strip(), bitrate, device, self.ignore_read_errors, self.read_retries, self.create_m3u, self.output_format), daemon=True).start()

    def on_cancel_rip(self, *_args):
        if not self.ripping:
            return
        self.cancel_requested.set()
        self.cancel_button.set_sensitive(False)
        proc = self.current_process
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self.set_status('Abbruch angefordert … der aktuelle Vorgang wird beendet.')

    def _run_cancellable(self, command, cwd=None, timeout=300):
        """Run a subprocess that can be stopped from the Cancel button."""
        if self.cancel_requested.is_set():
            return None
        proc = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.current_process = proc
        try:
            try:
                stdout, stderr = proc.communicate(timeout=0.25)
                return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                pass
            import time
            started = time.monotonic()
            while True:
                if self.cancel_requested.is_set():
                    proc.terminate()
                    try:
                        stdout, stderr = proc.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        stdout, stderr = proc.communicate()
                    return None
                if time.monotonic() - started > timeout:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                    raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
                try:
                    stdout, stderr = proc.communicate(timeout=0.25)
                    return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
                except subprocess.TimeoutExpired:
                    continue
        finally:
            self.current_process = None

    def rip_worker(self, selected, root, artist, album, year, bitrate, device, ignore_read_errors=False, read_retries=3, create_m3u=False, output_format='mp3'):
        album_dir = root / f'{clean_name(artist)} - {clean_name(album)}'
        try:
            root.mkdir(parents=True, exist_ok=True)
            album_dir.mkdir(parents=True, exist_ok=True)
            if self.cover_bytes:
                ext = '.png' if self.cover_bytes.startswith(b'\x89PNG\r\n\x1a\n') else ('.webp' if self.cover_bytes.startswith(b'RIFF') and self.cover_bytes[8:12] == b'WEBP' else '.jpg')
                (album_dir / f'cover{ext}').write_bytes(self.cover_bytes)

            # Read the disc in batch mode with one cdparanoia process. This avoids
            # restarting the drive reader between track 1 and track 2. cdparanoia
            # writes trackNN.cdda.wav files into the working directory.
            selected_numbers = {int(t['number']) for t in selected}
            requested_numbers = sorted(selected_numbers)
            if not requested_numbers:
                raise RuntimeError('Keine CD-Titel zum Auslesen gefunden.')
            # cdparanoia accepts one span argument, not a list of track numbers.
            # Group adjacent selected tracks into ranges (e.g. 1-2); separate
            # disjoint selections (e.g. 1 and 15) are read as separate spans.
            track_ranges = []
            for number in requested_numbers:
                if not track_ranges or number > track_ranges[-1][-1] + 1:
                    track_ranges.append([number])
                else:
                    track_ranges[-1].append(number)
            spans = [
                str(group[0]) if len(group) == 1 else f'{group[0]}-{group[-1]}'
                for group in track_ranges
            ]
            # cdparanoia may need several minutes per track on a scratched or
            # slow disc. The old timeout counted only the two endpoints of a
            # range, so a full 15-track range was killed after 360 seconds.
            # Budget time according to the actual number of tracks in each span.
            def span_timeout(span):
                ends = span.split('-', 1)
                count = int(ends[1]) - int(ends[0]) + 1 if len(ends) == 2 else 1
                return max(600, count * 600)
            total = len(selected)
            read_dir = None
            read_errors = ''
            with tempfile.TemporaryDirectory(prefix='lunaripper-cdda-') as temp_root:
                temp_root_path = Path(temp_root)
                attempts = max(1, int(read_retries) + 1)
                for attempt in range(attempts):
                    if self.cancel_requested.is_set():
                        raise RuntimeError('Rippen abgebrochen.')
                    attempt_dir = temp_root_path / f'normal-{attempt + 1}'
                    attempt_dir.mkdir()
                    self.set_status(('Lese nur ausgewählte Titel: ' + ', '.join(f'{n:02d}' for n in requested_numbers)) if attempt == 0 else f'Ausgewählte Titel werden erneut gelesen ({attempt}/{read_retries}) …')
                    try:
                        # Run each contiguous range with exactly one span argument.
                        # This avoids interpreting "1 2" as a start/end/output
                        # combination and still reads only the checked tracks.
                        for span in spans:
                            if self.cancel_requested.is_set():
                                raise RuntimeError('Rippen abgebrochen.')
                            rip = self._run_cancellable(
                                ['cdparanoia', '-B', '-d', device, span], cwd=str(attempt_dir),
                                timeout=span_timeout(span)
                            )
                            if rip is None:
                                raise RuntimeError('Rippen abgebrochen.')
                            read_errors = (rip.stderr or rip.stdout or read_errors)[-1000:]
                    except subprocess.TimeoutExpired:
                        read_errors = 'Zeitüberschreitung beim Auslesen der ausgewählten Titel.'
                    missing = [n for n in selected_numbers if not (attempt_dir / f'track{n:02d}.cdda.wav').is_file() or (attempt_dir / f'track{n:02d}.cdda.wav').stat().st_size <= 44]
                    if not missing:
                        read_dir = attempt_dir
                        break
                    if attempt + 1 < attempts:
                        self.set_status(f'CD-Lesefehler bei Titel(n) {", ".join(f"{n:02d}" for n in sorted(missing))}; ausgewählte Titel werden erneut gelesen …')

                # Optional best-effort pass: retry only the selected tracks with paranoia checks disabled.
                if read_dir is None and ignore_read_errors:
                    recovery_dir = temp_root_path / 'recovery'
                    recovery_dir.mkdir()
                    self.set_status('Normales Lesen fehlgeschlagen – starte Rettungsversuch nur für ausgewählte Titel …')
                    try:
                        for span in spans:
                            if self.cancel_requested.is_set():
                                raise RuntimeError('Rippen abgebrochen.')
                            recovery = self._run_cancellable(
                                ['cdparanoia', '-Z', '-B', '-d', device, span], cwd=str(recovery_dir),
                                timeout=span_timeout(span)
                            )
                            if recovery is None:
                                raise RuntimeError('Rippen abgebrochen.')
                            read_errors = (recovery.stderr or recovery.stdout or read_errors)[-1000:]
                    except subprocess.TimeoutExpired:
                        read_errors = 'Zeitüberschreitung beim Rettungsversuch für ausgewählte Titel.'
                    if any((recovery_dir / f'track{n:02d}.cdda.wav').is_file() and (recovery_dir / f'track{n:02d}.cdda.wav').stat().st_size > 44 for n in selected_numbers):
                        read_dir = recovery_dir

                if read_dir is None:
                    raise RuntimeError(f'CD-Auslesen fehlgeschlagen. Keine vollständigen Audiodaten für alle ausgewählten Titel. {read_errors}')

                for index, track in enumerate(selected, start=1):
                    if self.cancel_requested.is_set():
                        raise RuntimeError('Rippen abgebrochen.')
                    number = int(track['number'])
                    title = track.get('title') or f'Titel {number:02d}'
                    safe_title = clean_name(title, f'Titel {number:02d}')
                    stem = f'{number:02d} - {safe_title}'
                    out_mp3 = album_dir / f'{stem}.mp3'
                    out_wav = album_dir / f'{stem}.wav'
                    source_wav = read_dir / f'track{number:02d}.cdda.wav'
                    formats = set(output_format.split('_'))
                    need_mp3 = 'mp3' in formats
                    need_wav = 'wav' in formats
                    need_ogg = 'ogg' in formats
                    need_m4a = 'm4a' in formats
                    out_ogg = album_dir / f'{stem}.ogg'
                    out_m4a = album_dir / f'{stem}.m4a'
                    mp3_done = out_mp3.is_file() and out_mp3.stat().st_size > 0
                    wav_done = out_wav.is_file() and out_wav.stat().st_size > 44
                    ogg_done = out_ogg.is_file() and out_ogg.stat().st_size > 0
                    m4a_done = out_m4a.is_file() and out_m4a.stat().st_size > 0
                    if (not need_mp3 or mp3_done) and (not need_wav or wav_done) and (not need_ogg or ogg_done) and (not need_m4a or m4a_done):
                        self.set_status(f'Übersprungen, Ausgabedateien existieren bereits: {stem}')
                        GLib.idle_add(self.progress.set_fraction, index / total)
                        continue
                    if not source_wav.is_file() or source_wav.stat().st_size <= 44:
                        raise RuntimeError(f'Titel {number:02d} wurde nicht lesbar erzeugt.')
                    if need_wav and not wav_done:
                        partial_wav = out_wav.with_name(out_wav.name + '.part')
                        try:
                            partial_wav.unlink(missing_ok=True)
                            shutil.copyfile(source_wav, partial_wav)
                            if partial_wav.stat().st_size <= 44:
                                raise RuntimeError(f'WAV-Kopie von Titel {number} ist leer oder unvollständig.')
                            partial_wav.replace(out_wav)
                        finally:
                            partial_wav.unlink(missing_ok=True)
                    if need_ogg and not ogg_done:
                        if not shutil.which('oggenc'):
                            raise RuntimeError('Für OGG-Ausgabe fehlt oggenc. Bitte das Paket vorbis-tools installieren (sudo apt install vorbis-tools).')
                        self.set_status(f'Kodiere Titel {number:02d} ({index}/{total}) zu OGG …')
                        partial_ogg = out_ogg.with_name(out_ogg.name + '.part')
                        try:
                            partial_ogg.unlink(missing_ok=True)
                            enc = self._run_cancellable(['oggenc', '-q', '6', '-o', str(partial_ogg), str(source_wav)], timeout=300)
                            if enc is None:
                                raise RuntimeError('Rippen abgebrochen.')
                            if enc.returncode != 0 or not partial_ogg.exists() or partial_ogg.stat().st_size == 0:
                                raise RuntimeError(f'OGG-Kodierung von Titel {number} fehlgeschlagen: {(enc.stderr or enc.stdout)[-400:]}')
                            partial_ogg.replace(out_ogg)
                        finally:
                            partial_ogg.unlink(missing_ok=True)
                        try:
                            ogg_tags = OggVorbis(str(out_ogg))
                            ogg_tags['title'] = title
                            ogg_tags['artist'] = artist
                            ogg_tags['album'] = album
                            ogg_tags['tracknumber'] = str(number)
                            if year:
                                ogg_tags['date'] = year
                            ogg_tags.save()
                        except Exception as tag_exc:
                            self.set_status(f'OGG erstellt, aber Metadaten konnten nicht vollständig geschrieben werden: {tag_exc}')
                    if need_m4a and not m4a_done:
                        if not shutil.which('ffmpeg'):
                            raise RuntimeError('Für M4A-Ausgabe fehlt ffmpeg. Bitte das Paket installieren (sudo apt install ffmpeg).')
                        self.set_status(f'Kodiere Titel {number:02d} ({index}/{total}) zu M4A …')
                        partial_m4a = out_m4a.with_name(out_m4a.name + '.part.m4a')
                        try:
                            partial_m4a.unlink(missing_ok=True)
                            enc = self._run_cancellable(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source_wav), '-vn', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(partial_m4a)], timeout=600)
                            if enc is None:
                                raise RuntimeError('Rippen abgebrochen.')
                            if enc.returncode != 0 or not partial_m4a.exists() or partial_m4a.stat().st_size == 0:
                                raise RuntimeError(f'M4A-Kodierung von Titel {number} fehlgeschlagen: {((enc.stderr or enc.stdout) or "ffmpeg ohne Fehlertext")[-400:]}')
                            partial_m4a.replace(out_m4a)
                        finally:
                            partial_m4a.unlink(missing_ok=True)
                        try:
                            tags = MP4(str(out_m4a))
                            tags['\xa9nam'] = title
                            tags['\xa9ART'] = artist
                            tags['\xa9alb'] = album
                            tags['trkn'] = [(number, len(selected))]
                            if year:
                                tags['\xa9day'] = year
                            if self.cover_bytes:
                                if self.cover_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                                    cover_format = MP4Cover.FORMAT_PNG
                                else:
                                    cover_format = MP4Cover.FORMAT_JPEG
                                tags['covr'] = [MP4Cover(self.cover_bytes, imageformat=cover_format)]
                            tags.save()
                        except Exception as tag_exc:
                            self.set_status(f'M4A erstellt, aber Metadaten konnten nicht vollständig geschrieben werden: {tag_exc}')
                    if need_mp3 and not mp3_done:
                        self.set_status(f'Kodiere Titel {number:02d} ({index}/{total}) zu MP3 …')
                        partial_mp3 = out_mp3.with_name(out_mp3.name + '.part')
                        try:
                            partial_mp3.unlink(missing_ok=True)
                            enc = self._run_cancellable(['lame', '-b', bitrate, str(source_wav), str(partial_mp3)], timeout=300)
                            if enc is None:
                                raise RuntimeError('Rippen abgebrochen.')
                            if enc.returncode != 0 or not partial_mp3.exists() or partial_mp3.stat().st_size == 0:
                                raise RuntimeError(f'MP3-Kodierung von Titel {number} fehlgeschlagen: {(enc.stderr or enc.stdout)[-400:]}')
                            partial_mp3.replace(out_mp3)
                        finally:
                            partial_mp3.unlink(missing_ok=True)
                        try:
                            tags = ID3()
                            tags.add(TIT2(encoding=3, text=title))
                            tags.add(TPE1(encoding=3, text=artist))
                            tags.add(TALB(encoding=3, text=album))
                            tags.add(TRCK(encoding=3, text=str(number)))
                            if year: tags.add(TDRC(encoding=3, text=year))
                            if self.cover_bytes:
                                mime = 'image/png' if self.cover_bytes.startswith(b'\x89PNG\r\n\x1a\n') else ('image/webp' if self.cover_bytes.startswith(b'RIFF') and self.cover_bytes[8:12] == b'WEBP' else 'image/jpeg')
                                tags.add(APIC(encoding=3, mime=mime, type=3, desc='Cover', data=self.cover_bytes))
                            tags.save(out_mp3)
                        except Exception as tag_exc:
                            self.set_status(f'MP3 erstellt, aber ID3-Tags konnten nicht vollständig geschrieben werden: {tag_exc}')
                    GLib.idle_add(self.progress.set_fraction, index / total)
            if self.cancel_requested.is_set():
                self.set_status(f'Abgebrochen. Bereits fertige Ausgabedateien bleiben erhalten: {album_dir}')
            else:
                if create_m3u:
                    # Create the playlist only after ripping has finished, so it never interferes
                    # with the optical-drive read/write phase. Include only selected MP3s that exist.
                    playlist_tracks = []
                    for track in selected:
                        number = int(track['number'])
                        title = track.get('title') or f'Titel {number:02d}'
                        preferred_ext = '.mp3' if 'mp3' in set(output_format.split('_')) else ('.ogg' if 'ogg' in set(output_format.split('_')) else ('.m4a' if 'm4a' in set(output_format.split('_')) else '.wav'))
                        audio_path = album_dir / f'{number:02d} - {clean_name(title, f"Titel {number:02d}")}{preferred_ext}'
                        if audio_path.is_file() and audio_path.stat().st_size > 0:
                            playlist_tracks.append(audio_path.name)
                    if playlist_tracks:
                        playlist_path = album_dir / f'{clean_name(album)}.m3u'
                        playlist_path.write_text('#EXTM3U\n' + ''.join(name + '\n' for name in playlist_tracks), encoding='utf-8')
                self.set_status(f'Fertig! Dateien gespeichert in: {album_dir}')
        except Exception as exc:
            if self.cancel_requested.is_set():
                self.set_status('Rippen abgebrochen. Bereits fertige Ausgabedateien bleiben erhalten.')
            else:
                self.set_status(f'Fehler: {exc}')
        finally:
            self.ripping = False
            self.current_process = None
            GLib.idle_add(self.cancel_button.set_sensitive, False)
            GLib.idle_add(self.rip_button.set_sensitive, True)
            GLib.idle_add(self.scan_button.set_sensitive, True)
            GLib.idle_add(self.lookup_button.set_sensitive, True)


def main():
    app = LunaRipper()
    return app.run(None)

if __name__ == '__main__':
    raise SystemExit(main())
