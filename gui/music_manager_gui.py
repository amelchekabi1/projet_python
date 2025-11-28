# gui_full_integrated.py
"""
GUI integrated with your library modules.
- Uses PySide6 for GUI.
- Uses your library.DirectoryScanner, library.AudioFile, library.Playlist, library.xspf_writer when available.
- Falls back to mutagen/oswalk/simple classes if project modules missing.
- Playback via QtMultimedia when available, else pygame fallback (pygame is more reliable on Windows).
- Scanner runs in QThread and emits incremental events so UI stays responsive.

Save in project root and run: python gui_full_integrated.py
"""

import sys
import os
import io
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

# Ensure project root is importable (so "from library..." works)
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# GUI (PySide6)
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
        QLineEdit, QMessageBox, QSplitter, QFrame
    )
    from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
    from PySide6.QtGui import QPixmap, QFont
except Exception as e:
    print("PySide6 is required. Install with: pip install PySide6")
    raise

# Try QtMultimedia (optional)
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtCore import QUrl
    qt_multimedia_available = True
except Exception:
    qt_multimedia_available = False

# Try pygame fallback for playback
try:
    import pygame
    pygame_available = True
except Exception:
    pygame_available = False

# Mutagen for metadata fallback
try:
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3
    mutagen_available = True
except Exception:
    mutagen_available = False

# Pillow for cover image processing (optional)
try:
    from PIL import Image
    pillow_available = True
except Exception:
    pillow_available = False

# Try to import project modules (preferred)
use_project_library = False
try:
    from library.directory_scanner import DirectoryScanner  # type: ignore
    from library.audiofile import AudioFile  # type: ignore
    from library.playlist import Playlist as ProjectPlaylist, Track as ProjectTrack  # type: ignore
    from library.xspf_writer import write_xspf  # type: ignore
    use_project_library = True
except Exception:
    DirectoryScanner = None
    AudioFile = None
    ProjectPlaylist = None
    ProjectTrack = None
    write_xspf = None

# ----------------------------
# Lightweight fallback models
# ----------------------------
@dataclass
class SimpleTrack:
    path: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None

    def display(self) -> str:
        return f"{self.artist or 'Inconnu'} — {self.title or Path(self.path).name}"

class SimplePlaylist:
    def __init__(self, name="Playlist"):
        self.name = name
        self.tracks: List[SimpleTrack] = []

    def add_track(self, t: SimpleTrack):
        self.tracks.append(t)

    def remove_track(self, index: int):
        if 0 <= index < len(self.tracks):
            self.tracks.pop(index)

# ----------------------------
# Utility helpers
# ----------------------------
def human_duration(sec: Optional[int]) -> str:
    if not sec:
        return "-"
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"

def extract_cover_bytes(path: str) -> Optional[bytes]:
    """Try to get embedded cover bytes using mutagen (MP3/FLAC)."""
    if not mutagen_available:
        return None
    try:
        p = Path(path)
        if p.suffix.lower() == ".mp3":
            try:
                id3 = ID3(path)
            except Exception:
                return None
            for key in id3.keys():
                if key.startswith("APIC"):
                    apic = id3.get(key)
                    if hasattr(apic, "data"):
                        return apic.data
        elif p.suffix.lower() == ".flac":
            f = FLAC(path)
            pics = list(f.pictures)
            if pics:
                return pics[0].data
    except Exception:
        return None
    return None

def qpix_from_bytes(data: bytes, max_size=(320,320)) -> QPixmap:
    """Convert image bytes to QPixmap (uses Pillow when available)."""
    pix = QPixmap()
    if not pillow_available:
        pix.loadFromData(data)
        return pix
    try:
        img = Image.open(io.BytesIO(data))
        img.thumbnail(max_size)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pix.loadFromData(buf.getvalue())
        return pix
    except Exception:
        try:
            pix.loadFromData(data)
            return pix
        except Exception:
            return QPixmap()

# ----------------------------
# Scanner thread (non-blocking)
# ----------------------------
class ScannerThread(QThread):
    file_found = Signal(str)
    progress = Signal(int)     # 0-100
    finished = Signal(list)
    status = Signal(str)

    def __init__(self, folder: str, sanity_check: bool = True):
        super().__init__()
        self.folder = folder
        self._running = True
        self.sanity_check = sanity_check

    def stop(self):
        self._running = False

    def run(self):
        self.status.emit("Lancement du scan...")
        if DirectoryScanner:
            try:
                # Use project DirectoryScanner (preferred)
                ds = DirectoryScanner(sanity_check_with_mutagen=self.sanity_check)
                files = list(ds.scan(self.folder))
                total = len(files)
                if total == 0:
                    self.progress.emit(100)
                    self.finished.emit([])
                    self.status.emit("Aucun fichier trouvé.")
                    return
                for i, f in enumerate(files, start=1):
                    if not self._running:
                        break
                    self.file_found.emit(str(f))
                    pct = int(i / total * 100)
                    self.progress.emit(pct)
                    time.sleep(0.01)  # tiny pause so user can see progress
                self.finished.emit(files[:i])
                self.status.emit(f"Scan terminé — {min(i,total)} fichier(s).")
                return
            except Exception as e:
                # fallback to pure python scanning
                self.status.emit(f"Scanner projet indisponible ({e}), fallback.")
        # Fallback scanning using os.walk and optional mutagen sanity check
        found = []
        all_paths = []
        for root, _, files in os.walk(self.folder):
            for name in files:
                all_paths.append(os.path.join(root, name))
        total = len(all_paths) if all_paths else 1
        checked = 0
        for full in all_paths:
            if not self._running:
                break
            checked += 1
            if not full.lower().endswith((".mp3", ".flac")):
                continue
            if self.sanity_check and mutagen_available:
                try:
                    from mutagen import File as MutagenFile
                    mf = MutagenFile(full)
                    if mf is None:
                        continue
                except Exception:
                    continue
            found.append(full)
            self.file_found.emit(full)
            self.progress.emit(int(checked / total * 100))
            time.sleep(0.01)
        self.finished.emit(found)
        self.status.emit(f"Scan fallback terminé — {len(found)} fichier(s).")

# ----------------------------
# Player wrapper: QMediaPlayer preferred, else pygame fallback
# ----------------------------
class Player:
    def __init__(self):
        self.mode = None
        self.qt_player = None
        self.qt_audio_out = None
        if qt_multimedia_available:
            try:
                self.qt_audio_out = QAudioOutput()
                self.qt_player = QMediaPlayer()
                self.qt_player.setAudioOutput(self.qt_audio_out)
                self.mode = "qt"
            except Exception:
                self.mode = None
        if self.mode is None and pygame_available:
            try:
                import pygame
                pygame.mixer.init()
                self.mode = "pygame"
            except Exception:
                self.mode = None

    def play(self, path: str):
        if self.mode == "qt":
            try:
                url = QUrl.fromLocalFile(path)
                self.qt_player.setSource(url)
                self.qt_player.play()
                return
            except Exception:
                pass
        if self.mode == "pygame":
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            except Exception as e:
                raise

    def pause(self):
        if self.mode == "qt":
            try:
                self.qt_player.pause()
            except Exception:
                pass
        elif self.mode == "pygame":
            pygame.mixer.music.pause()

    def resume(self):
        if self.mode == "qt":
            try:
                self.qt_player.play()
            except Exception:
                pass
        elif self.mode == "pygame":
            pygame.mixer.music.unpause()

    def stop(self):
        if self.mode == "qt":
            try:
                self.qt_player.stop()
            except Exception:
                pass
        elif self.mode == "pygame":
            pygame.mixer.music.stop()

# ----------------------------
# Main GUI window
# ----------------------------
class MusicManagerMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Opti Music — Gestionnaire de bibliothèque")
        self.resize(1100, 700)

        # Central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # Left - Scanner
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, 3)

        lbl_scan = QLabel("Scanner")
        lbl_scan.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        left_layout.addWidget(lbl_scan)

        row = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Dossier à scanner...")
        btn_browse = QPushButton("Parcourir")
        btn_browse.clicked.connect(self.browse_folder)
        btn_scan = QPushButton("Scanner")
        btn_scan.clicked.connect(self.start_scan)
        row.addWidget(self.folder_input)
        row.addWidget(btn_browse)
        row.addWidget(btn_scan)
        left_layout.addLayout(row)

        self.scan_progress = QProgressBar()
        self.scan_progress.setValue(0)
        left_layout.addWidget(self.scan_progress)

        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.on_file_double_click)
        left_layout.addWidget(self.file_list)

        btn_add_sel = QPushButton("Ajouter sélection → Playlist")
        btn_add_sel.clicked.connect(self.add_selected_to_playlist)
        left_layout.addWidget(btn_add_sel)

        # Middle - Playlist
        middle_layout = QVBoxLayout()
        main_layout.addLayout(middle_layout, 3)

        lbl_pl = QLabel("Playlist")
        lbl_pl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        middle_layout.addWidget(lbl_pl)

        self.playlist_widget = QListWidget()
        self.playlist_widget.itemClicked.connect(self.on_playlist_item_clicked)
        middle_layout.addWidget(self.playlist_widget)

        row2 = QHBoxLayout()
        btn_up = QPushButton("▲")
        btn_down = QPushButton("▼")
        btn_remove = QPushButton("Supprimer")
        btn_save = QPushButton("Enregistrer XSPF")
        btn_up.clicked.connect(self.move_up)
        btn_down.clicked.connect(self.move_down)
        btn_remove.clicked.connect(self.remove_playlist_item)
        btn_save.clicked.connect(self.save_playlist)
        row2.addWidget(btn_up)
        row2.addWidget(btn_down)
        row2.addWidget(btn_remove)
        row2.addWidget(btn_save)
        middle_layout.addLayout(row2)

        # Right - Metadata & Player
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, 2)

        lbl_info = QLabel("Infos / Lecture")
        lbl_info.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        right_layout.addWidget(lbl_info)

        self.cover_label = QLabel("No cover")
        self.cover_label.setFixedSize(320, 320)
        self.cover_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)

        self.meta_title = QLabel("Titre: -")
        self.meta_artist = QLabel("Artiste: -")
        self.meta_album = QLabel("Album: -")
        self.meta_duration = QLabel("Durée: -")
        for w in (self.meta_title, self.meta_artist, self.meta_album, self.meta_duration):
            w.setStyleSheet("padding:4px;")
            right_layout.addWidget(w)

        # Playback controls
        controls = QHBoxLayout()
        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("▶")
        self.btn_pause = QPushButton("⏸")
        self.btn_stop = QPushButton("⏹")
        for b in (self.btn_prev, self.btn_play, self.btn_pause, self.btn_stop):
            b.setFixedHeight(40)
            b.setFixedWidth(60)
        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_pause)
        controls.addWidget(self.btn_stop)
        right_layout.addLayout(controls)

        self.btn_play.clicked.connect(self.play_selected)
        self.btn_pause.clicked.connect(self.pause_clicked)
        self.btn_stop.clicked.connect(self.stop_clicked)
        self.btn_prev.clicked.connect(self.prev_clicked)

        self.play_progress = QProgressBar()
        self.play_progress.setValue(0)
        right_layout.addWidget(self.play_progress)

        # Status bar
        self.status = self.statusBar()

        # Player and state
        self.player = Player()
        self.scanner: Optional[ScannerThread] = None
        self.found_files: List[str] = []
        # Use project Playlist if available, else fallback
        self.playlist = ProjectPlaylist("GUI Playlist") if ProjectPlaylist else SimplePlaylist("GUI Playlist")

    # -------------------------
    # Left panel handlers
    # -------------------------
    def browse_folder(self):
        p = QFileDialog.getExistingDirectory(self, "Choisir dossier musical")
        if p:
            self.folder_input.setText(p)

    def start_scan(self):
        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.warning(self, "Avertissement", "Sélectionnez un dossier à scanner.")
            return
        if not os.path.isdir(folder):
            QMessageBox.critical(self, "Erreur", "Le dossier n'existe pas.")
            return
        # reset UI
        self.file_list.clear()
        self.scan_progress.setValue(0)
        # stop previous thread if running
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
        self.scanner = ScannerThread(folder, sanity_check=True)
        self.scanner.file_found.connect(self._on_file_found)
        self.scanner.progress.connect(self.scan_progress.setValue)
        self.scanner.finished.connect(self._on_scan_finished)
        self.scanner.status.connect(self.status.showMessage)
        self.scanner.start()
        self.status.showMessage("Scan lancé...")

    def _on_file_found(self, path: str):
        item = QListWidgetItem(Path(path).name)
        item.setData(Qt.ItemDataRole.UserRole, path)
        self.file_list.addItem(item)

    def _on_scan_finished(self, files: List[str]):
        self.found_files = files
        self.scan_progress.setValue(100)
        self.status.showMessage(f"Scan terminé — {len(files)} fichier(s) trouvé(s).")

    def on_file_double_click(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.show_metadata_for_path(path)

    # -------------------------
    # Metadata display
    # -------------------------
    def show_metadata_for_path(self, path: str):
        # prefer project AudioFile if available
        title = Path(path).name
        artist = "Inconnu"
        album = "Inconnu"
        duration_txt = "-"
        duration_sec = None
        try:
            if AudioFile:
                af = AudioFile.from_path(path)
                md = af.read_metadata()
                title = md.title or title
                artist = md.artist or artist
                album = md.album or album
                duration_sec = md.duration_sec
                duration_txt = human_duration(duration_sec)
            elif mutagen_available:
                if path.lower().endswith(".mp3"):
                    f = MP3(path)
                    title = f.tags.get("TIT2").text[0] if f.tags and "TIT2" in f.tags else title
                    artist = f.tags.get("TPE1").text[0] if f.tags and "TPE1" in f.tags else artist
                    album = f.tags.get("TALB").text[0] if f.tags and "TALB" in f.tags else album
                    duration_txt = human_duration(int(f.info.length) if f.info else None)
                else:
                    f = FLAC(path)
                    title = f.get("title", [title])[0]
                    artist = f.get("artist", [artist])[0]
                    album = f.get("album", [album])[0]
                    duration_txt = human_duration(int(f.info.length) if f.info else None)
        except Exception as e:
            self.status.showMessage(f"Erreur métadonnées: {e}")

        self.meta_title.setText(f"Titre: {title}")
        self.meta_artist.setText(f"Artiste: {artist}")
        self.meta_album.setText(f"Album: {album}")
        self.meta_duration.setText(f"Durée: {duration_txt}")

        # cover
        cover_bytes = extract_cover_bytes(path)
        if cover_bytes:
            pix = qpix_from_bytes(cover_bytes, max_size=(320,320))
            if not pix.isNull():
                self.cover_label.setPixmap(pix.scaled(320,320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        # fallback look for sidecar images
        folder = Path(path).parent
        for name in ("cover.jpg", "folder.jpg", "cover.png"):
            c = folder / name
            if c.exists():
                pix = QPixmap(str(c)).scaled(320,320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cover_label.setPixmap(pix)
                return
        # else reset placeholder
        self.cover_label.setText("No cover")

    # -------------------------
    # Playlist actions
    # -------------------------
    def add_selected_to_playlist(self):
        items = self.file_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Info", "Sélectionnez des fichiers à ajouter.")
            return
        for it in items:
            path = it.data(Qt.ItemDataRole.UserRole)
            # collect metadata if possible
            title = Path(path).stem
            artist = None
            album = None
            duration = None
            try:
                if AudioFile:
                    af = AudioFile.from_path(path)
                    md = af.read_metadata()
                    title = md.title or title
                    artist = md.artist
                    album = md.album
                    duration = md.duration_sec
            except Exception:
                pass
            # create project Track if available
            if ProjectTrack and ProjectPlaylist:
                try:
                    t = ProjectTrack(path, title=title, artist=artist, album=album, duration=duration)
                    self.playlist.add_track(t)
                except Exception:
                    st = SimpleTrack(path, title=title, artist=artist, album=album, duration=duration)
                    if isinstance(self.playlist, SimplePlaylist):
                        self.playlist.add_track(st)
            else:
                st = SimpleTrack(path, title=title, artist=artist, album=album, duration=duration)
                if isinstance(self.playlist, SimplePlaylist):
                    self.playlist.add_track(st)
            # update UI
            self.playlist_widget.addItem(Path(path).name)

    def on_playlist_item_clicked(self, item: QListWidgetItem):
        idx = self.playlist_widget.row(item)
        try:
            tr = self.playlist.tracks[idx]
            path = tr.path if hasattr(tr, "path") else tr
            self.show_metadata_for_path(path)
        except Exception:
            pass

    def move_up(self):
        idx = self.playlist_widget.currentRow()
        if idx <= 0:
            return
        item = self.playlist_widget.takeItem(idx)
        self.playlist_widget.insertItem(idx-1, item)
        # swap in model
        try:
            self.playlist.tracks[idx-1], self.playlist.tracks[idx] = self.playlist.tracks[idx], self.playlist.tracks[idx-1]
        except Exception:
            pass

    def move_down(self):
        idx = self.playlist_widget.currentRow()
        if idx < 0 or idx >= self.playlist_widget.count()-1:
            return
        item = self.playlist_widget.takeItem(idx)
        self.playlist_widget.insertItem(idx+1, item)
        try:
            self.playlist.tracks[idx+1], self.playlist.tracks[idx] = self.playlist.tracks[idx], self.playlist.tracks[idx+1]
        except Exception:
            pass

    def remove_playlist_item(self):
        idx = self.playlist_widget.currentRow()
        if idx < 0:
            return
        self.playlist_widget.takeItem(idx)
        try:
            self.playlist.remove_track(idx)
        except Exception:
            if isinstance(self.playlist, SimplePlaylist):
                self.playlist.remove_track(idx)

    def save_playlist(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Enregistrer playlist", "", "XSPF files (*.xspf)")
        if not filename:
            return
        try:
            # Prefer project write_xspf if available and playlist is project type
            if write_xspf and hasattr(self.playlist, "tracks"):
                write_xspf(self.playlist, filename)
            else:
                # fallback writer: convert to SimplePlaylist and write
                from xml.etree import ElementTree as ET
                pl = SimplePlaylist(Path(filename).stem)
                for t in self.playlist.tracks:
                    p = t.path if hasattr(t, "path") else t
                    st = SimpleTrack(p, title=(t.title if hasattr(t, "title") else None),
                                     artist=(t.artist if hasattr(t, "artist") else None),
                                     album=(t.album if hasattr(t, "album") else None),
                                     duration=(t.duration if hasattr(t, "duration") else None))
                    pl.add_track(st)
                # write XSPF
                root = ET.Element("playlist", version="1", xmlns="http://xspf.org/ns/0/")
                title_el = ET.SubElement(root, "title"); title_el.text = pl.name
                tl = ET.SubElement(root, "trackList")
                for t in pl.tracks:
                    tr_el = ET.SubElement(tl, "track")
                    loc = ET.SubElement(tr_el, "location"); loc.text = f"file://{t.path}"
                    if t.title: ET.SubElement(tr_el, "title").text = t.title
                    if t.artist: ET.SubElement(tr_el, "creator").text = t.artist
                    if t.album: ET.SubElement(tr_el, "album").text = t.album
                    if t.duration: ET.SubElement(tr_el, "duration").text = str(t.duration)
                tree = ET.ElementTree(root)
                tree.write(filename, encoding="utf-8", xml_declaration=True)
            QMessageBox.information(self, "Succès", f"Playlist enregistrée : {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer la playlist : {e}")

    # -------------------------
    # Playback controls
    # -------------------------
    def play_selected(self):
        idx = self.playlist_widget.currentRow()
        if idx < 0:
            QMessageBox.information(self, "Info", "Aucun élément sélectionné dans la playlist.")
            return
        tr = self.playlist.tracks[idx]
        path = tr.path if hasattr(tr, "path") else tr
        try:
            self.player.play(path)
            self.status.showMessage(f"Lecture: {Path(path).name}")
            # optional: could start a QTimer to update play_progress using mutagen duration
        except Exception as e:
            QMessageBox.critical(self, "Erreur lecture", f"Impossible de lancer la lecture : {e}")

    def pause_clicked(self):
        try:
            # if using pygame, this toggles pause/resume manually
            if self.player.mode == "pygame":
                pygame.mixer.music.pause()
                self.status.showMessage("Lecture en pause")
            else:
                self.player.pause()
                self.status.showMessage("Lecture en pause")
        except Exception:
            pass

    def stop_clicked(self):
        try:
            self.player.stop()
            self.status.showMessage("Lecture arrêtée")
            self.play_progress.setValue(0)
        except Exception:
            pass

    def prev_clicked(self):
        idx = self.playlist_widget.currentRow()
        if idx > 0:
            self.playlist_widget.setCurrentRow(idx-1)
            self.play_selected()

# ----------------------------
# Run
# ----------------------------
def main():
    app = QApplication(sys.argv)
    win = MusicManagerMain()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()