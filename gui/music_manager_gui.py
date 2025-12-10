# gui_full_integrated.py
"""
Gestionnaire musical GUI — Interface PySide6 pour parcourir, afficher et lire des fichiers audio.
Ce module assemble un scanner asynchrone, un lecteur (QtMultimedia ou fallback pygame),
l'affichage des métadonnées et des pochettes, et une UI animée. Conçu pour être lisible et extensible.
Les classes principales sont ScannerThread, Player et MusicManagerMain.
"""

import sys
import os
import io
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
import math  # ajouté près des autres imports de la librairie standard

# Import des composants Qt nécessaires (widgets, layouts, etc.).
# Les imports PySide6 sont regroupés ci-dessous ; certains éléments sont
# utilisés seulement si les modules optionnels (ex: QtMultimedia) sont
# présents.
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
    QLineEdit, QMessageBox, QSplitter, QFrame, QStackedLayout
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer, QPointF
from PySide6.QtGui import QPixmap, QFont, QPainter, QPainterPath, QColor, QPen
from PySide6.QtGui import QPixmap, QFont, QPainter, QPainterPath, QColor, QPen, QFontDatabase


# S'assurer que la racine du projet est importable (pour pouvoir faire
# `from library...`). Cela facilite l'exécution depuis le répertoire racine
# sans configuration supplémentaire du PYTHONPATH.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Bloc d'initialisation GUI (PySide6)
# Le bloc `try` ci-dessous vérifie la disponibilité de PySide6. S'il manque
# des composants, on affiche un message expliquant la dépendance et on lève
# l'exception afin d'arrêter l'exécution (la GUI ne peut pas fonctionner
# sans PySide6).
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

# Tentative d'import de QtMultimedia (optionnel)
# Si présent, `QMediaPlayer` et `QAudioOutput` seront utilisés pour la
# lecture audio (gestion native par Qt). Sinon, le code basculera vers un
# lecteur de secours (pygame) défini plus bas.
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtCore import QUrl
    qt_multimedia_available = True
except Exception:
    qt_multimedia_available = False

# Fallback : pygame pour la lecture
# pygame est utilisé comme solution de secours lorsque QtMultimedia n'est
# pas disponible ; il est souvent fiable sur Windows.
try:
    import pygame
    pygame_available = True
except Exception:
    pygame_available = False

# Mutagen : extraction des métadonnées et pochettes
# Mutagen permet d'accéder aux tags ID3 (MP3) et Vorbis Comment (FLAC),
# ainsi qu'aux images intégrées. Lorsqu'il est absent, certaines
# fonctionnalités (extraction de la pochette) seront désactivées.
try:
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import ID3
    import base64
    mutagen_available = True
except Exception:
    mutagen_available = False

# Pillow (PIL) : traitement d'image pour les pochettes
# Si Pillow est disponible, on redimensionne proprement les images avant de
# les convertir en `QPixmap` afin d'améliorer la qualité d'affichage.
try:
    from PIL import Image
    pillow_available = True
except Exception:
    pillow_available = False

# Import des modules du package `library` (préférentiel)
# Si le package `library` est installé dans le projet, ses classes seront
# utilisées. À défaut, le module continue à fonctionner grâce à des
# implémentations de repli déclarées plus bas dans ce fichier.
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

# Fonction utilitaire : enregistre la pochette (cover) intégrée du fichier
# sélectionné dans la playlist. Elle lit l'octet d'image via
# `extract_cover_bytes` et ouvre un dialogue pour demander où sauvegarder.
def save_cover_image(self):
    """Enregistrer la pochette intégrée d'une piste sélectionnée.

    Fonction utilitaire appelée depuis l'UI. Elle :
    - récupère l'élément sélectionné dans la playlist,
    - extrait les octets de la pochette (via extract_cover_bytes),
    - ouvre un dialogue pour demander le chemin de sauvegarde,
    - écrit le fichier sur disque et notifie l'utilisateur.
    """
    item = self.playlist_widget.currentItem()
    if not item:
        QMessageBox.warning(self, "Avertissement", "Aucune musique sélectionnée.")
        return

    path = item.data(Qt.ItemDataRole.UserRole)
    if not path:
        QMessageBox.warning(self, "Erreur", "Impossible de récupérer le chemin du fichier.")
        return

    data = extract_cover_bytes(path)
    if not data:
        QMessageBox.warning(self, "Avertissement", "Aucune cover trouvée dans ce fichier.")
        return

    # Demande à l'utilisateur où sauvegarder la pochette
    save_path, _ = QFileDialog.getSaveFileName(
        self,
        "Enregistrer la cover",
        "cover.png",
        "Images (*.png *.jpg *.jpeg)"
    )
    if not save_path:
        return

    try:
        with open(save_path, "wb") as f:
            f.write(data)
        QMessageBox.information(self, "Succès", "Cover enregistrée avec succès.")
    except Exception as e:
        QMessageBox.critical(self, "Erreur", f"Échec de l'enregistrement: {e}")


# Lightweight fallback models
# Ces classes servent de repli si les classes du package `library`
# ne sont pas disponibles : elles stockent les infos essentielles
# d'une piste et d'une playlist.
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
    # Playlist simple de repli (contient une liste de SimpleTrack)
    def __init__(self, name="Playlist"):
        self.name = name
        self.tracks: List[SimpleTrack] = []

    def add_track(self, t: SimpleTrack):
        self.tracks.append(t)

    def remove_track(self, index: int):
        if 0 <= index < len(self.tracks):
            self.tracks.pop(index)

# Utility helpers
# Fonctions utilitaires réutilisées par l'interface : formatage durée,
# extraction de pochette depuis les métadonnées, conversion en QPixmap, etc.
def human_duration(sec: Optional[int]) -> str:
    """Formate une durée (en secondes) vers une chaîne 'M:SS'.

    Parameters
    ----------
    sec : Optional[int]
        Durée en secondes. Si None ou 0, retourne '-'.

    Returns
    -------
    str
        Chaîne formatée sous la forme 'M:SS'.
    """
    if not sec:
        return "-"
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"

def extract_cover_bytes(path: str) -> Optional[bytes]:
    """Extraire les octets d'une pochette embarquée depuis un fichier audio.

    Supporte les formats MP3 (ID3 APIC) et FLAC (pictures) via mutagen si disponible.
    Retourne les octets d'image (bytes) ou None si aucune image trouvée ou si mutagen absent.

    Parameters
    ----------
    path : str
        Chemin vers le fichier audio.

    Returns
    -------
    Optional[bytes]
        Octets de l'image ou None.
    """
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
    """Convertir des octets d'image en QPixmap en respectant max_size.

    Si Pillow est disponible, on redimensionne l'image proprement (thumbnail) pour améliorer la qualité.
    Cela facilite l'affichage dans l'UI sans altérer la logique de l'application.

    Parameters
    ----------
    data : bytes
        Données brutes de l'image.
    max_size : tuple, optional
        Taille maximale (largeur, hauteur) pour le thumbnail.

    Returns
    -------
    QPixmap
        Pixmap utilisable dans les widgets Qt.
    """
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


# Scanner thread (non-blocking)
# Classe qui parcourt le dossier en tâche de fond pour trouver des fichiers
# audio sans bloquer l'interface. Elle émet des signaux Qt pour
# notifier l'UI (fichier trouvé, progression, statut, terminé).
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
        # Démarre le scan : on prévient l'UI que le scan commence.
        self.status.emit("Lancement du scan (fallback)...")
        found = []
        all_paths = []
        for root, _, files in os.walk(self.folder):
            for name in files:
                all_paths.append(os.path.join(root, name))

        total = len(all_paths) if all_paths else 1
        checked = 0

        # Parcours des chemins collectés : on filtre par extension et on
        # émet un signal à chaque fichier pertinent (pour mise à jour UI)
        for full in all_paths:
            if not self._running:
                break
            checked += 1
            # Filtrer seulement par extension
            if full.lower().endswith((".mp3", ".flac")):
                found.append(full)
                self.file_found.emit(full)
            self.progress.emit(int(checked / total * 100))
            time.sleep(0.01)

        self.finished.emit(found)
        self.status.emit(f"Scan fallback terminé — {len(found)} fichier(s).")


class AnimatedContainer(QFrame):
    """
    Conteneur Qt personnalisé dessinant une animation organique en arrière-plan.

    Usage :
    - Placé derrière des widgets transparents (overlay) pour fournir un rendu visuel moderne.
    - L'animation est pilotée par un QTimer interne qui déclenche update() (~60fps).
    - Ne gère pas d'état d'application : purement visuel, modifiable pour personnalisation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AnimatedContainer")
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: transparent;")
        self._start_ms = time.time() * 1000.0
        self._rotation_speed = 0.0006
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(16)
        self._debug_fill = False  # mettre True pour afficher un remplissage magenta de débogage

    def sizeHint(self):
        p = self.parent()
        if p is not None:
            return QSize(max(200, p.width()), max(200, p.height()))
        return QSize(600, 400)

    def minimumSizeHint(self):
        return QSize(100, 80)

    def paintEvent(self, event):
        # paintEvent : appelé par Qt quand il faut redessiner le widget.
        # Nous utilisons QPainter pour dessiner des formes animées.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        w = max(1, rect.width())
        h = max(1, rect.height())
        cx = w / 2.0
        cy = h / 2.0
        now_ms = (time.time() * 1000.0 - self._start_ms)
        rotation = (now_ms * self._rotation_speed) % (2 * math.pi)

        if self._debug_fill:
            painter.fillRect(rect, QColor(255, 0, 255, 60))

        base_radius = min(w, h) * 0.30
        orbital_radius = min(w, h) * 0.22
        num_points = 30

        # Fonction interne pour construire la forme d'un blob organique.
        def make_blob(center_x, center_y, radius, wobble_amount, angle_offset):
            pts = []
            time_factor = now_ms / 200.0
            for i in range(num_points):
                angle = (i / num_points) * 2 * math.pi + angle_offset
                wobble = wobble_amount * math.sin(angle * 5 + time_factor)
                r = radius + wobble
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                pts.append(QPointF(x, y))
            path = QPainterPath()
            if pts:
                path.moveTo(pts[0])
                for p in pts[1:]:
                    path.lineTo(p)
                path.closeSubpath()
            return path

        # Alpha réduits pour que la playlist reste lisible
        yellow = QColor(250, 220, 60, 110)   # alpha réduit
        blue   = QColor(70, 180, 230, 100)
        green  = QColor(100, 200, 70, 120)

        yellow_angle = rotation + (math.pi / 2)
        blue_angle = rotation + (math.pi * 3 / 2)

        ycx = cx + orbital_radius * math.cos(yellow_angle)
        ycy = cy + orbital_radius * math.sin(yellow_angle)

        bcx = cx + orbital_radius * math.cos(blue_angle)
        bcy = cy + orbital_radius * math.sin(blue_angle)

        painter.fillPath(make_blob(ycx, ycy, base_radius * 0.95, base_radius * 0.10, yellow_angle), yellow)
        painter.fillPath(make_blob(bcx, bcy, base_radius * 0.95, base_radius * 0.10, blue_angle), blue)
        painter.fillPath(make_blob(cx, cy, base_radius * 1.08, base_radius * 0.12, 0), green)

        # --- DRAW "CY" TEXT with soft shadow & reduced opacity ---
        text = "CY"
        font_size = int(base_radius * 0.95)  # taille proche du blob vert
        if font_size < 8:
            font_size = 8
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)

        # Ombre (douce, légèrement décalée)
        shadow_color = QColor(0, 0, 0, 90)
        painter.setPen(shadow_color)
        shadow_rect = rect.translated(3, 4)
        painter.drawText(shadow_rect, Qt.AlignCenter, text)

        # Texte principal: blanc semi-transparent pour laisser transparaître les blobs
        text_color = QColor(255, 255, 255, 150)  # opacité réduite
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignCenter, text)

        painter.end()

        




# Player wrapper: QMediaPlayer preferred, else pygame fallback
# Classe qui encapsule le lecteur audio. Elle choisit le moteur disponible
# (QtMultimedia ou pygame) et fournit des méthodes simples : play/pause/stop.
# ----------------------------
# Fournit : play(path, start_ms=0), pause(), resume(), stop(), set_position(ms), get_position_ms()
# Maintient : current_path, is_paused, is_playing pour permettre à l'UI de décider s'il faut reprendre ou relancer.
# Comportement en cas de fallback : le code essaie d'abord QtMultimedia, puis pygame si Qt indisponible.
class Player:
    """Wrapper unifiant deux moteurs audio : QtMultimedia (préféré) ou pygame (fallback).

    Interface exposée :
    - play(path, start_ms=0)
    - pause()
    - resume()
    - stop()
    - set_position(ms)
    - get_position_ms()

    Comportements clés :
    - Conserve current_path, is_paused, is_playing pour des décisions UI (resume vs reload).
    - Tente d'utiliser QMediaPlayer/QAudioOutput si disponibles, sinon initie pygame.mixer.
    - Les méthodes gèrent les incompatibilités entre moteurs en mode 'best-effort'.
    """
    def __init__(self):
        self.mode = None
        self.qt_player = None
        self.qt_audio_out = None
        self.current_path: Optional[str] = None
        self.is_paused = False
        self.is_playing = False

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

    def play(self, path: str, start_ms: int = 0):
        """Démarrer la lecture de `path`. Si même chemin et en pause, reprendre au lieu de recharger.
           start_ms permet de commencer à partir d'une milliseconde spécifique (Qt fonctionne de manière fiable).
        """
        if self.mode == "qt":
            try:
                if path != self.current_path:
                    url = QUrl.fromLocalFile(path)
                    self.qt_player.setSource(url)
                    self.current_path = path
                if start_ms is not None and hasattr(self.qt_player, "setPosition"):
                    try:
                        self.qt_player.setPosition(int(start_ms))
                    except Exception:
                        pass
                self.qt_player.play()
                self.is_paused = False
                self.is_playing = True
                return
            except Exception:
                pass

        if self.mode == "pygame":
            try:
                import pygame
                # Si même fichier et actuellement en pause -> unpause
                if path == self.current_path and self.is_paused:
                    try:
                        pygame.mixer.music.unpause()
                        self.is_paused = False
                        self.is_playing = True
                        return
                    except Exception:
                        pass
                # sinon charger et jouer (le seek de pygame est limité et dépend du format)
                if path != self.current_path:
                    pygame.mixer.music.load(path)
                    self.current_path = path
                # convertir ms -> s pour l'argument start de pygame (peut ne pas fonctionner pour tous les formats)
                if start_ms and hasattr(pygame.mixer.music, "play"):
                    sec = float(start_ms) / 1000.0
                    try:
                        pygame.mixer.music.play(loops=0, start=sec)
                    except TypeError:
                        # les anciennes versions de pygame peuvent ne pas accepter start en kwarg ; essayer positionnel
                        try:
                            pygame.mixer.music.play(0, sec)
                        except Exception:
                            pygame.mixer.music.play()
                else:
                    pygame.mixer.music.play()
                self.is_paused = False
                self.is_playing = True
            except Exception as e:
                raise

    def pause(self):
        if self.mode == "qt":
            try:
                self.qt_player.pause()
            except Exception:
                pass
        elif self.mode == "pygame":
            try:
                import pygame
                pygame.mixer.music.pause()
            except Exception:
                pass
        self.is_paused = True
        self.is_playing = False

    def resume(self):
        if self.mode == "qt":
            try:
                self.qt_player.play()
            except Exception:
                pass
        elif self.mode == "pygame":
            try:
                import pygame
                pygame.mixer.music.unpause()
            except Exception:
                pass
        self.is_paused = False
        self.is_playing = True

    def stop(self):
        if self.mode == "qt":
            try:
                self.qt_player.stop()
            except Exception:
                pass
        elif self.mode == "pygame":
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.is_paused = False
        self.is_playing = False
        # ne pas effacer current_path — garde la référence pour que les décisions de reprise soient possibles

    def set_position(self, ms: int):
        if self.mode == "qt":
            try:
                self.qt_player.setPosition(int(ms))
            except Exception:
                pass
        elif self.mode == "pygame":
            # le positionnement/seek de pygame est peu fiable selon les formats ; on tente le mieux possible :
            try:
                import pygame
                sec = float(ms) / 1000.0
                # recharger puis jouer à la position (peut redémarrer le décodage)
                if self.current_path:
                    pygame.mixer.music.load(self.current_path)
                    try:
                        pygame.mixer.music.play(loops=0, start=sec)
                    except TypeError:
                        try:
                            pygame.mixer.music.play(0, sec)
                        except Exception:
                            pygame.mixer.music.play()
            except Exception:
                pass

    def get_position_ms(self) -> int:
        if self.mode == "qt":
            try:
                return int(self.qt_player.position() or 0)
            except Exception:
                return 0
        elif self.mode == "pygame":
            try:
                import pygame
                pos = pygame.mixer.music.get_pos()
                return int(pos if pos and pos > 0 else 0)
            except Exception:
                return 0
        return 0


# Main GUI window :

# Fenêtre principale de l'application
# Contient la construction complète de l'interface (scanner, playlist,
# métadonnées, contrôles de lecture) et les handlers associés.
class MusicManagerMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Opti Music — Gestionnaire de bibliothèque")
        self.resize(1100, 700)
        # Modern app stylesheet (conserve l'animation inchangée)
        # Application d'une feuille de style CSS pour uniformiser l'apparence de l'UI (couleurs, boutons, listes).
        try:
            QApplication.instance().setStyleSheet("""
                /* Base */
                QWidget { font-family: 'Segoe UI', Arial, sans-serif; color: #E6EEF3; }
                QMainWindow { background: #0F1720; } /* fond sombre */
                QLabel { color: #DDE9F2; font-size: 13px; }

                /* Inputs and lists */
                QLineEdit, QListWidget, QProgressBar {
                    background: rgba(255,255,255,0.03);
                    border: 1px solid rgba(255,255,255,0.04);
                    border-radius: 8px;
                    padding: 6px;
                    color: #E6EEF3;
                }
                QListWidget::item { padding: 8px 10px; margin: 2px 0; }
                QListWidget::item:selected { background: rgba(255,255,255,0.04); color: #FFFFFF; }

                /* Buttons */
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2b3440, stop:1 #25303a);
                    color: #E6EEF3;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 8px;
                }
                QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #33404c, stop:1 #28343e); }
                QPushButton:pressed { background: #1f2a31; }

                /* Progress bar */
                QProgressBar {
                    border-radius: 6px;
                    text-align: center;
                    height: 10px;
                }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #76c7ff, stop:1 #58a6f0);
                }

                /* Make cover label area stand out */
                QLabel#coverLabel {
                    background: rgba(255,255,255,0.02);
                    border-radius: 8px;
                }
            """)
        except Exception:
            pass
        # Tentative d'utilisation de la police Inter (locale ou système) ; sinon Segoe UI.
        try:
            db = QFontDatabase()
            inter_file = PROJECT_ROOT / "fonts" / "Inter-Regular.ttf"   # police locale optionnelle si fournie
            if inter_file.exists():
                fid = db.addApplicationFont(str(inter_file))
                families = db.applicationFontFamilies(fid) if fid != -1 else []
                if families:
                    QApplication.instance().setFont(QFont(families[0], 10, QFont.Weight.DemiBold))
                else:
                    QApplication.instance().setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
            else:
                # essayer la police Inter du système, sinon revenir à Segoe UI
                QApplication.instance().setFont(QFont("Inter", 10, QFont.Weight.DemiBold))
        except Exception:
            QApplication.instance().setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))


        # Central widget and layout
        # Widget central : layout horizontal contenant trois colonnes :
        # - gauche : scanner (sélection et résultats du scan)
        # - milieu : playlist (avec animation visuelle en arrière-plan)
        # - droite : métadonnées et contrôles de lecture
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # Left - Scanner
        # Colonne de gauche : permet de choisir un dossier et de lancer
        # le scan asynchrone des fichiers audio.
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, 3)

        lbl_scan = QLabel("Scanner")
        lbl_scan.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        left_layout.addWidget(lbl_scan)

        row = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Dossier à scanner...")
        btn_browse = QPushButton("Choisir dossier musical")
        btn_browse.clicked.connect(self.browse_folder)
        row.addWidget(self.folder_input)
        row.addWidget(btn_browse)
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
        # Colonne centrale : affiche la playlist et contient l'animation
        # d'arrière-plan via `AnimatedContainer`.
        middle_layout = QVBoxLayout()
        main_layout.addLayout(middle_layout, 3)

        lbl_pl = QLabel("Playlist")
        lbl_pl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        middle_layout.addWidget(lbl_pl)

        # Animated container (peint l'arrière-plan)
        # Conteneur animé : dessine l'animation organique en arrière-plan.
        # L'overlay (widgets interactifs) est placé par-dessus pour conserver la réactivité.
        container = AnimatedContainer()
        from PySide6.QtWidgets import QSizePolicy
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Overlay widget that holds the interactive playlist on top
        # Overlay : widget superposé contenant la liste interactive (playlist) et ses contrôles.
        overlay = QWidget(container)
        overlay.setAttribute(Qt.WA_TranslucentBackground, True)
        overlay.setStyleSheet("background: transparent;")
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(6, 6, 6, 6)

        # Playlist widget (transparent pour laisser transparaître le container)
        # Widget de playlist avec fond transparent afin que l'animation reste visible.
        self.playlist_widget = QListWidget()
        self.playlist_widget.itemClicked.connect(self.on_playlist_item_clicked)
        self.playlist_widget.setStyleSheet("""
            QListWidget { background: transparent; }
            QListView, QListWidget, QListWidget::item { background: transparent; }
            QListWidget::item:selected { background: rgba(255,255,255,40); }
        """)
        self.playlist_widget.setAutoFillBackground(False)
        try:
            self.playlist_widget.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        except:
            pass

        overlay_layout.addWidget(self.playlist_widget)

        # Put overlay into container layout so it fills the same area
        # Insère l'overlay dans le layout du container pour qu'il occupe exactement la même surface.
        cont_layout = QVBoxLayout(container)
        cont_layout.setContentsMargins(0, 0, 0, 0)
        cont_layout.addWidget(overlay)

        # Keep refs for debug if needed
        # Conserver des références utiles au débogage (taille, état).
        self._anim_container = container
        self._overlay = overlay

        # Add container to middle layout (animation is drawn by the container)
        # Ajouter le container à la colonne centrale ; l'animation y est rendue.
        middle_layout.addWidget(container)

        # Buttons row (actions sur la playlist)
        # Rangée de boutons : déplacer, supprimer, sauvegarder la playlist, télécharger la pochette.
        row2 = QHBoxLayout()
        btn_up = QPushButton("▲")
        btn_down = QPushButton("▼")
        btn_remove = QPushButton("Supprimer")
        btn_save = QPushButton("Enregistrer XSPF")
        btn_cover = QPushButton("Télécharger cover")

        btn_up.clicked.connect(self.move_up)
        btn_down.clicked.connect(self.move_down)
        btn_remove.clicked.connect(self.remove_playlist_item)
        btn_save.clicked.connect(self.save_playlist)
        btn_cover.clicked.connect(lambda: save_cover_image(self))

        btn_load = QPushButton("Charger XSPF")
        btn_load.clicked.connect(self.load_playlist)

        row2.addWidget(btn_up)
        row2.addWidget(btn_down)
        row2.addWidget(btn_remove)
        row2.addWidget(btn_save)
        row2.addWidget(btn_cover)
        row2.addWidget(btn_load)

        middle_layout.addLayout(row2)


        # Right - Metadata & Player
        # Colonne de droite : métadonnées (titre, artiste, album, durée), pochette et contrôles.
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, 2)

        lbl_info = QLabel("Infos / Lecture")
        lbl_info.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        right_layout.addWidget(lbl_info)

        # modern cover area
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(300, 300)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                border-radius: 18px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #111217, stop:1 #1e2430);
                padding: 0;
            }
        """)
        self.cover_label.setScaledContents(True)
        right_layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)

        # dynamic time label and thin progress line
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #cfd8e3; padding:4px; font-weight:600;")
        right_layout.addWidget(self.time_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet("""
        QProgressBar {
            background-color: #262b33;
            border-radius: 3px;
        }
        QProgressBar::chunk {
            background-color: #5cb3ff;
            border-radius: 3px;
        }
        """)
        right_layout.addWidget(self.progress_bar)

        #NOUVELLE SECTION MÉTADONNÉES AVEC BOUTONS
        meta_frame = QFrame()
        meta_layout = QVBoxLayout(meta_frame)
        
        self.meta_title = QLabel("Titre: -")
        self.meta_artist = QLabel("Artiste: -")
        self.meta_album = QLabel("Album: -")
        self.meta_duration = QLabel("Durée: -")
        for w in (self.meta_title, self.meta_artist, self.meta_album, self.meta_duration):
            w.setStyleSheet("padding:4px;")
            meta_layout.addWidget(w)
        
        #NOUVEAUX BOUTONS POUR LES MÉTADONNÉES
        meta_btn_row = QHBoxLayout()
        btn_edit_tags = QPushButton("Modifier TAGS")
        btn_search_api = QPushButton("Rechercher API")
        btn_dl_cover = QPushButton("Télécharger cover")
        
        btn_edit_tags.clicked.connect(self.edit_tags)
        btn_search_api.clicked.connect(self.search_online_metadata)
        btn_dl_cover.clicked.connect(self.download_cover_online)
        
        meta_btn_row.addWidget(btn_edit_tags)
        meta_btn_row.addWidget(btn_search_api)
        meta_btn_row.addWidget(btn_dl_cover)
        meta_layout.addLayout(meta_btn_row)
        
        right_layout.addWidget(meta_frame)

        # Playback controls
        # Boutons de contrôle de lecture : précédent, play, pause, suivant.
        controls = QHBoxLayout()
        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("▶")
        self.btn_pause = QPushButton("⏸")
        self.btn_next = QPushButton("⏭")
        for b in (self.btn_prev, self.btn_play, self.btn_pause, self.btn_next):
            b.setFixedHeight(44)
            b.setFixedWidth(64)
        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_pause)
        controls.addWidget(self.btn_next)
        right_layout.addLayout(controls)
        modern_btn = """
        QPushButton {
            background: #22272f;
            color: #e6eef3;
            border: none;
            border-radius: 12px;
            padding: 8px;
            font-size: 18px;
        }
        QPushButton:hover {
            background: #2f3640;
        }
        QPushButton:pressed {
            background: #181a1d;
        }
        """
        for b in (self.btn_prev, self.btn_play, self.btn_pause, self.btn_next):
            b.setStyleSheet(modern_btn)


        self.btn_play.clicked.connect(self.play_selected)
        self.btn_pause.clicked.connect(self.pause_clicked)
        self.btn_next.clicked.connect(self.next_clicked)
        self.btn_prev.clicked.connect(self.prev_clicked)


        # Status bar
        # Barre d'état Qt : affichage de messages courts et retours d'opération pour l'utilisateur.
        self.status = self.statusBar()

        # Player and state
        # Instance du wrapper Player et initialisation des variables d'état (positions, index, timers).
        self.player = Player()

        # playback timing / progress plumbing
        # Temporisation lecture et gestion de la progression (stockage en ms).
        self._total_ms = 0
        self._current_ms = 0
        # index of the currently-playing track in the playlist (-1 none)
        # Index de la piste courante dans la playlist (-1 = aucune).
        self._current_index = -1
        # playback state helpers
        # Aides pour l'état de lecture : historiques d'appui, protection contre triggers multiples.
        self._current_index = -1
        self._last_prev_click = 0.0        # timestamp pour comportement avancé du bouton précédent
        self._end_triggered = False        # évite les déclenchements multiples de fin de piste
        # connect end-of-media (Qt) if available
        # Connecter la détection de fin de lecture native Qt si disponible.
        if qt_multimedia_available and getattr(self.player, "qt_player", None):
            try:
                self.player.qt_player.mediaStatusChanged.connect(self._on_media_status)
            except Exception:
                pass



        # If QtMultimedia is available, connect to position/duration signals
        # Si QtMultimedia est disponible, lier les signaux de position/durée pour mise à jour UI.
        if qt_multimedia_available and getattr(self.player, "qt_player", None):
            try:
                self.player.qt_player.positionChanged.connect(self._on_position_changed)
                self.player.qt_player.durationChanged.connect(self._on_duration_changed)
            except Exception:
                pass
        # else use pygame polling timer (if pygame available)
        # Sinon, si on utilise pygame, démarrer un timer Qt périodique pour sonder la position.
        elif pygame_available:
            self._pygame_timer = QTimer(self)
            self._pygame_timer.setInterval(400)
            self._pygame_timer.timeout.connect(self._update_pygame_progress)

        self.scanner: Optional[ScannerThread] = None
        self.found_files: List[str] = []
        # Use project Playlist if available, else fallback
        # Utiliser la Playlist du package projet si présente, sinon utiliser le SimplePlaylist de repli.
        self.playlist = ProjectPlaylist("GUI Playlist") if ProjectPlaylist else SimplePlaylist("GUI Playlist")

    
    # Left panel handlers
    
    # Ouvre un dialogue pour choisir un dossier et lance le scan.
    def browse_folder(self):
        p = QFileDialog.getExistingDirectory(self, "Choisir dossier musical")
        if p:
            self.folder_input.setText(p)
            QTimer.singleShot(100, self.start_scan)

    # Prépare et démarre le thread de scan (ScannerThread).
    # Vérifie le dossier, réinitialise l'UI et connecte les signaux.
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
        
    # Playback controls (pro)
    
    def _play_index(self, index: int, start_ms: int = 0):
        """Sélectionne la ligne de la playlist et démarre la lecture à start_ms (ms)."""
        count = self.playlist_widget.count()
        if index < 0 or index >= count:
            return
        # select row in UI and update model index
        # Sélectionner la ligne dans l'UI et mettre à jour l'index du modèle.
        self.playlist_widget.setCurrentRow(index)
        self._current_index = index
        self._end_triggered = False   # permettre à la fin de piste de se déclencher de nouveau pour la nouvelle piste

        # try to get path from model or UI item
        # Récupérer le chemin depuis le modèle (si présent) sinon depuis l'élément UI.
        try:
            tr = self.playlist.tracks[index]
            path = tr.path if hasattr(tr, "path") else tr
        except Exception:
            item = self.playlist_widget.currentItem()
            path = item.data(Qt.ItemDataRole.UserRole) if item else None

        if not path:
            return

        # show metadata for selected track (ensures right info in the right column)
        # Afficher les métadonnées de la piste sélectionnée (synchronise les colonnes).
        try:
            self.show_metadata_for_path(path)
        except Exception:
            pass

        # start playback (Player.play supports start_ms)
        # Démarrer la lecture ; Player.play supporte start_ms pour reprendre depuis une position.
        try:
            self.player.play(path, start_ms=start_ms)
            # start pygame timer if pygame fallback
            # Si on utilise pygame en repli, démarrer le timer de sondage pour mettre à jour la progression.
            if pygame_available and getattr(self.player, "mode", None) == "pygame":
                if getattr(self, "_pygame_timer", None):
                    self._pygame_timer.start()
            self.status.showMessage(f"Lecture: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur lecture", f"Impossible de lancer la lecture : {e}")


    def play_selected(self):
        """Jouer ou reprendre l'élément sélectionné en fonction de l'état courant."""
        idx = self.playlist_widget.currentRow()
        if idx < 0:
            QMessageBox.information(self, "Info", "Aucun élément sélectionné dans la playlist.")
            return

        # find selected path
        try:
            tr = self.playlist.tracks[idx]
            path = tr.path if hasattr(tr, "path") else tr
        except Exception:
            item = self.playlist_widget.currentItem()
            path = item.data(Qt.ItemDataRole.UserRole) if item else None

        if not path:
            return

        # If same path and paused -> resume from stored position
        if getattr(self.player, "current_path", None) == path and getattr(self.player, "is_paused", False):
            try:
                self.player.resume()
                if pygame_available and getattr(self, "_pygame_timer", None):
                    self._pygame_timer.start()
                self.status.showMessage("Reprise de la lecture")
                return
            except Exception:
                pass

        # If same path and playing -> do nothing
        if getattr(self.player, "current_path", None) == path and getattr(self.player, "is_playing", False):
            self.status.showMessage("Déjà en lecture")
            return

        # Otherwise start track. If we previously had a _current_ms for this track, use it; else 0
        start_ms = 0
        if getattr(self, "_current_index", -1) == idx and getattr(self, "_current_ms", 0):
            start_ms = self._current_ms
        self._play_index(idx, start_ms=start_ms)

    def pause_clicked(self):
        """Met la lecture en pause (conserve la position courante)."""
        try:
            self.player.pause()
            # stop pygame timer if used
            if pygame_available and getattr(self, "_pygame_timer", None) is not None:
                try:
                    self._pygame_timer.stop()
                except Exception:
                    pass
            self.status.showMessage("Lecture en pause")
        except Exception:
            pass

    def next_clicked(self):
        """Aller à la piste suivante (boucle vers la première si fin de liste)."""
        count = self.playlist_widget.count()
        if count == 0:
            return
        # prefer explicit current index if set
        idx = self._current_index if getattr(self, "_current_index", -1) >= 0 else self.playlist_widget.currentRow()
        if idx < 0:
            idx = 0
        next_idx = (idx + 1) % count
        self._play_index(next_idx, start_ms=0)

    def prev_clicked(self):
        """Comportement du bouton 'précédent' :
        - si la position courante > 2s et que l'utilisateur n'a pas appuyé rapidement deux fois -> relancer la piste courante
        - si double-appui rapide ou position <= 2s -> passer à la piste précédente (avec wrap)
        """
        import time
        now = time.time()
        click_gap = 0.6  # seconds: quick double-press window
        count = self.playlist_widget.count()
        if count == 0:
            return
        idx = self._current_index if getattr(self, "_current_index", -1) >= 0 else self.playlist_widget.currentRow()
        if idx < 0:
            idx = 0

        cur_ms = getattr(self, "_current_ms", 0)
        # if > threshold and NOT a quick second click -> restart current
        if cur_ms > 2000 and (now - getattr(self, "_last_prev_click", 0.0) > click_gap):
            self._play_index(idx, start_ms=0)
            # ensure UI shows 0 immediately to avoid flash of old time
            self._current_ms = 0
            try:
                self.progress_bar.setValue(0)
                self.time_label.setText(f"{self._format_ms(0)} / {self._format_ms(self._total_ms)}")
            except Exception:
                pass
            self._last_prev_click = now
            return


        # else go previous (wrap to last if currently first)
        prev_idx = (idx - 1) % count
        self._play_index(prev_idx, start_ms=0)
        self._last_prev_click = now


    
    # Position/duration handlers
    
    def _on_media_status(self, status):
        """Gestionnaire Qt pour la fin de média : avance automatiquement à la piste suivante."""
        try:
            from PySide6.QtMultimedia import QMediaPlayer
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                # protect against multiple signals firing: small delay then next
                if not getattr(self, "_end_triggered", False):
                    self._end_triggered = True
                    QTimer.singleShot(80, self.next_clicked)
        except Exception:
            pass

    def _format_ms(self, ms: int) -> str:
        """Formate une durée en millisecondes vers 'M:SS' (0 -> '0:00')."""
        try:
            if not ms or int(ms) <= 0:
                return "0:00"
            s_total = int(ms) // 1000
            m, s = divmod(s_total, 60)
            return f"{m}:{s:02d}"
        except Exception:
            return "0:00"


    def _on_duration_changed(self, d: int):
        # d est en millisecondes pour QMediaPlayer
        # Met à jour la durée totale connue et ajuste la barre de progression.
        try:
            self._total_ms = int(d or 0)
        except Exception:
            self._total_ms = 0
        if self._total_ms > 0:
            self.progress_bar.setMaximum(self._total_ms)
            self.time_label.setText(f"{self._format_ms(0)} / {self._format_ms(self._total_ms)}")
        else:
            self.progress_bar.setMaximum(100)
            self.time_label.setText("0:00 / 0:00")

    def _on_position_changed(self, pos: int):
        # pos est en millisecondes
        # Met à jour la position courante et l'UI (barre + étiquette).
        try:
            self._current_ms = int(pos or 0)
        except Exception:
            self._current_ms = 0
        # update UI
        try:
            self.progress_bar.setValue(self._current_ms)
        except Exception:
            pass
        self.time_label.setText(f"{self._format_ms(self._current_ms)} / {self._format_ms(self._total_ms)}")

    def _update_pygame_progress(self):
        # pygame.mixer.music.get_pos retourne le temps en ms depuis le début de la lecture,
        # ou une valeur négative lorsque l'état est inconnu/arrêté.
        try:
            import pygame
            pos = pygame.mixer.music.get_pos()
        except Exception:
            pos = -1
        if pos is None or pos < 0:
            # arrêté ou état inconnu : rien à faire
            return
        # si nous disposons déjà d'une durée provenant des métadonnées, la préférer pour la progression
        total_ms = getattr(self, "_total_ms", 0)
        if total_ms == 0:
            # tenter de récupérer la durée stockée en secondes définie par show_metadata_for_path
            total_ms = int(getattr(self, "_duration_sec", 0) * 1000) if getattr(self, "_duration_sec", None) else 0
            self._total_ms = total_ms
            if total_ms > 0:
                self.progress_bar.setMaximum(total_ms)
        self._current_ms = pos
        # si nous connaissons total_ms et que nous sommes près de la fin, avancer une fois (fallback pygame)
        try:
            if getattr(self, "_total_ms", 0) > 0 and not getattr(self, "_end_triggered", False):
                # si dans les 500ms avant la fin, considérer comme terminé (éviter les -1 instables)
                if self._current_ms >= max(0, self._total_ms - 500):
                    self._end_triggered = True
                    QTimer.singleShot(80, self.next_clicked)
        except Exception:
            pass

        try:
            self.progress_bar.setValue(self._current_ms)
        except Exception:
            pass
        self.time_label.setText(f"{self._format_ms(self._current_ms)} / {self._format_ms(self._total_ms)}")
    
    # Handler appelé par ScannerThread pour chaque fichier trouvé.
    # Ajoute l'élément à la liste des fichiers à l'écran.
    def _on_file_found(self, path: str):
        item = QListWidgetItem(Path(path).name)
        item.setData(Qt.ItemDataRole.UserRole, path)
        self.file_list.addItem(item)

    # Handler appelé quand le scan est terminé : met à jour l'état.
    def _on_scan_finished(self, files: List[str]):
        self.found_files = files
        self.scan_progress.setValue(100)
        self.status.showMessage(f"Scan terminé — {len(files)} fichier(s) trouvé(s).")

    # Double-clic sur un fichier : affiche ses métadonnées.
    def on_file_double_click(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.show_metadata_for_path(path)

    
    # Metadata display
    
    # Lit et affiche les métadonnées d'un fichier (titre, artiste, album,
    # durée) et affiche la pochette si elle est trouvée.
    def show_metadata_for_path(self, path: str):
        # prefer project AudioFile if available
        title = Path(path).name
        artist = "Inconnu"
        album = "Inconnu"
        duration_txt = "-"
        duration_sec = None

        #read metadata first
        try:
            if AudioFile:
                af = AudioFile.from_path(path)
                md = af.read_metadata()
                title = md.title or title
                artist = md.artist or artist
                album = md.album or album
                duration_sec = md.duration_sec or duration_sec
                if duration_sec:
                    duration_txt = human_duration(duration_sec)
            elif mutagen_available:
                if path.lower().endswith(".mp3"):
                    f = MP3(path)
                    title = f.tags.get("TIT2").text[0] if f.tags and "TIT2" in f.tags else title
                    artist = f.tags.get("TPE1").text[0] if f.tags and "TPE1" in f.tags else artist
                    album = f.tags.get("TALB").text[0] if f.tags and "TALB" in f.tags else album
                    duration_sec = int(f.info.length) if getattr(f, "info", None) else None
                    if duration_sec:
                        duration_txt = human_duration(duration_sec)
                else:
                    f = FLAC(path)
                    title = f.get("title", [title])[0]
                    artist = f.get("artist", [artist])[0]
                    album = f.get("album", [album])[0]
                    duration_sec = int(f.info.length) if getattr(f, "info", None) else None
                    if duration_sec:
                        duration_txt = human_duration(duration_sec)
        except Exception as e:
            self.status.showMessage(f"Erreur métadonnées: {e}")

        #store duration for progress AFTER reading metadata
        self._duration_sec = duration_sec or 0
        self._total_ms = int((duration_sec or 0) * 1000)
        if self._total_ms > 0:
            try:
                self.progress_bar.setMaximum(self._total_ms)
            except Exception:
                pass
            self.time_label.setText(f"{self._format_ms(0)} / {self._format_ms(self._total_ms)}")
        else:
            self.progress_bar.setMaximum(100)
            self.time_label.setText("0:00 / 0:00")

        # update metadata labels
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


    
    # Playlist actions
    
    # Ajoute les fichiers sélectionnés dans la liste de gauche à la
    # playlist centrale (évite les doublons et collecte les métadonnées).
    def add_selected_to_playlist(self):
        items = self.file_list.selectedItems()
        if not items:
            QMessageBox.information(self, "Info", "Sélectionnez des fichiers à ajouter.")
            return
        for it in items:
            path = it.data(Qt.ItemDataRole.UserRole)
            # Prevent duplicates in playlist
            filename = Path(path).name
            for i in range(self.playlist_widget.count()):
                   if self.playlist_widget.item(i).text() == filename:
                     QMessageBox.information(self, "Info", "La musique est déjà dans la playlist.")
                     return

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
            item = QListWidgetItem(filename)
            item.setData(Qt.ItemDataRole.UserRole, path)   # <<< REQUIRED
            self.playlist_widget.addItem(item)

    # Clic sur un élément de la playlist : affiche ses métadonnées.
    def on_playlist_item_clicked(self, item: QListWidgetItem):
        idx = self.playlist_widget.row(item)
        try:
            tr = self.playlist.tracks[idx]
            path = tr.path if hasattr(tr, "path") else tr
            self.show_metadata_for_path(path)
        except Exception:
            pass

    # Déplace l'élément sélectionné d'une position vers le haut
    # à la fois dans l'UI et, si possible, dans le modèle de playlist.
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

    # Déplace l'élément sélectionné d'une position vers le bas
    # à la fois dans l'UI et, si possible, dans le modèle de playlist.
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

    # Supprime l'élément sélectionné de la playlist (UI + modèle).
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

    # Enregistre la playlist au format XSPF. Utilise la fonction
    # `write_xspf` du projet si disponible, sinon écrit un XML de repli.
    def save_playlist(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Enregistrer playlist", "", "XSPF files (*.xspf)")
        if not filename:
            return
        try:
            # Préférence : utiliser la fonction write_xspf du package projet si disponible.
            if write_xspf and hasattr(self.playlist, "tracks"):
                write_xspf(self.playlist, filename)
            else:
                # écrivain de repli : conversion en SimplePlaylist puis écriture XML XSPF
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

    
    # NOUVELLES FONCTIONNALITÉS AJOUTÉES
    
    
    def load_playlist(self):
        """Charger une playlist XSPF existante depuis un fichier.
        
        Cette méthode permet de :
        - Ouvrir un dialogue de sélection de fichier XSPF
        - Parser le fichier XML avec gestion du namespace XSPF
        - Vider la playlist actuelle
        - Charger toutes les pistes avec leurs métadonnées
        - Mettre à jour l'interface graphique
        
        Le parsing gère à la fois les fichiers avec et sans namespace XML.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Ouvrir playlist", "", "XSPF files (*.xspf)")
        if not filename:
            return
        
        try:
            from xml.etree import ElementTree as ET
            tree = ET.parse(filename)
            root = tree.getroot()
            
            # Vider la playlist actuelle
            self.playlist_widget.clear()
            if ProjectPlaylist:
                self.playlist = ProjectPlaylist(Path(filename).stem)
            else:
                self.playlist = SimplePlaylist(Path(filename).stem)
            
            # Parser avec namespace XSPF
            ns = {'xspf': 'http://xspf.org/ns/0/'}
            tracks = root.findall('.//xspf:track', ns)
            
            if not tracks:
                # Essayer sans namespace si aucun résultat
                tracks = root.findall('.//track')
            
            for track_el in tracks:
                # Extraire le chemin du fichier
                loc_el = track_el.find('xspf:location', ns) if track_el.find('xspf:location', ns) is not None else track_el.find('location')
                if loc_el is None or not loc_el.text:
                    continue
                
                path = loc_el.text.replace("file://", "")
                if not Path(path).exists():
                    continue
                
                # Extraire les métadonnées
                title_el = track_el.find('xspf:title', ns) if track_el.find('xspf:title', ns) is not None else track_el.find('title')
                artist_el = track_el.find('xspf:creator', ns) if track_el.find('xspf:creator', ns) is not None else track_el.find('creator')
                album_el = track_el.find('xspf:album', ns) if track_el.find('xspf:album', ns) is not None else track_el.find('album')
                duration_el = track_el.find('xspf:duration', ns) if track_el.find('xspf:duration', ns) is not None else track_el.find('duration')
                
                title = title_el.text if title_el is not None and title_el.text else Path(path).stem
                artist = artist_el.text if artist_el is not None else None
                album = album_el.text if album_el is not None else None
                duration = int(duration_el.text) if duration_el is not None and duration_el.text else None
                
                # Ajouter à la playlist
                if ProjectTrack:
                    try:
                        t = ProjectTrack(path, title=title, artist=artist, album=album, duration=duration)
                        self.playlist.add_track(t)
                    except:
                        st = SimpleTrack(path, title=title, artist=artist, album=album, duration=duration)
                        self.playlist.add_track(st)
                else:
                    st = SimpleTrack(path, title=title, artist=artist, album=album, duration=duration)
                    self.playlist.add_track(st)
                
                # Mettre à jour l'interface
                item = QListWidgetItem(Path(path).name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.playlist_widget.addItem(item)
            
            QMessageBox.information(self, "Succès", f"Playlist chargée : {len(tracks)} piste(s)")
            self.status.showMessage(f"Playlist chargée : {filename}", 5000)
        
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger la playlist : {e}")

    def edit_tags(self):
        """Modifier les TAGS (métadonnées) d'un fichier audio MP3 ou FLAC.
        
        Cette méthode permet de :
        - Sélectionner un fichier dans la playlist
        - Lire les métadonnées actuelles (titre, artiste, album)
        - Afficher un dialogue d'édition
        - Sauvegarder les modifications directement dans le fichier
        - Rafraîchir l'affichage des métadonnées
        
        Nécessite la bibliothèque Mutagen pour modifier les fichiers.
        Supporte les formats MP3 (ID3) et FLAC (Vorbis Comment).
        """
        item = self.playlist_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Avertissement", "Aucune musique sélectionnée.")
            return
        
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "Erreur", "Fichier introuvable.")
            return
        
        # Lire les métadonnées actuelles
        title = artist = album = ""
        try:
            if mutagen_available:
                if path.lower().endswith(".mp3"):
                    f = MP3(path)
                    title = f.tags.get("TIT2").text[0] if f.tags and "TIT2" in f.tags else ""
                    artist = f.tags.get("TPE1").text[0] if f.tags and "TPE1" in f.tags else ""
                    album = f.tags.get("TALB").text[0] if f.tags and "TALB" in f.tags else ""
                else:
                    f = FLAC(path)
                    title = f.get("title", [""])[0]
                    artist = f.get("artist", [""])[0]
                    album = f.get("album", [""])[0]
        except:
            pass
        
        # Créer le dialogue d'édition
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier les TAGS")
        layout = QFormLayout(dialog)
        
        title_edit = QLineEdit(title)
        artist_edit = QLineEdit(artist)
        album_edit = QLineEdit(album)
        
        layout.addRow("Titre:", title_edit)
        layout.addRow("Artiste:", artist_edit)
        layout.addRow("Album:", album_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            # Sauvegarder les modifications
            try:
                if not mutagen_available:
                    QMessageBox.warning(self, "Erreur", "Mutagen n'est pas disponible pour modifier les TAGS.")
                    return
                
                if path.lower().endswith(".mp3"):
                    from mutagen.id3 import TIT2, TPE1, TALB
                    f = MP3(path)
                    if not f.tags:
                        f.add_tags()
                    f.tags["TIT2"] = TIT2(encoding=3, text=title_edit.text())
                    f.tags["TPE1"] = TPE1(encoding=3, text=artist_edit.text())
                    f.tags["TALB"] = TALB(encoding=3, text=album_edit.text())
                    f.save()
                else:
                    f = FLAC(path)
                    f["title"] = title_edit.text()
                    f["artist"] = artist_edit.text()
                    f["album"] = album_edit.text()
                    f.save()
                
                QMessageBox.information(self, "Succès", "TAGS modifiés avec succès.")
                # Rafraîchir l'affichage des métadonnées
                self.show_metadata_for_path(path)
            
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de modifier les TAGS : {e}")

    def search_online_metadata(self):
        """Rechercher les métadonnées en ligne via l'API MusicBrainz.
        
        Cette méthode permet de :
        - Rechercher des informations sur un morceau via MusicBrainz
        - Afficher jusqu'à 5 résultats avec détails complets
        - Montrer titre, artiste(s), album, et ID MusicBrainz
        
        L'API MusicBrainz est une base de données musicale libre et ouverte.
        Nécessite la bibliothèque 'requests' pour les appels HTTP.
        
        Format de recherche : "artist:NomArtiste AND recording:TitreMorceau"
        """
        item = self.playlist_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Avertissement", "Aucune musique sélectionnée.")
            return
        
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        
        # Récupérer les métadonnées actuelles pour la recherche
        try:
            if mutagen_available:
                if path.lower().endswith(".mp3"):
                    f = MP3(path)
                    artist = f.tags.get("TPE1").text[0] if f.tags and "TPE1" in f.tags else ""
                    title = f.tags.get("TIT2").text[0] if f.tags and "TIT2" in f.tags else ""
                else:
                    f = FLAC(path)
                    artist = f.get("artist", [""])[0]
                    title = f.get("title", [""])[0]
            else:
                artist = title = ""
        except:
            artist = title = ""
        
        # Créer le dialogue de recherche
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox, QTextEdit
        dialog = QDialog(self)
        dialog.setWindowTitle("Rechercher métadonnées en ligne")
        dialog.resize(500, 400)
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        artist_edit = QLineEdit(artist)
        title_edit = QLineEdit(title)
        form.addRow("Artiste:", artist_edit)
        form.addRow("Titre:", title_edit)
        layout.addLayout(form)
        
        btn_search = QPushButton("Rechercher")
        layout.addWidget(btn_search)
        
        result_text = QTextEdit()
        result_text.setReadOnly(True)
        layout.addWidget(result_text)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        def perform_search():
            """Fonction interne pour effectuer la recherche API."""
            result_text.clear()
            artist_query = artist_edit.text().strip()
            title_query = title_edit.text().strip()
            
            if not artist_query and not title_query:
                result_text.setText("Veuillez entrer au moins un artiste ou un titre.")
                return
            
            result_text.setText("Recherche en cours...\n")
            
            try:
                import requests
                # Utilisation de l'API MusicBrainz
                query = f"artist:{artist_query} AND recording:{title_query}" if artist_query and title_query else artist_query or title_query
                url = f"https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json&limit=5"
                
                response = requests.get(url, headers={'User-Agent': 'MusicManager/1.0'}, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    recordings = data.get('recordings', [])
                    
                    if not recordings:
                        result_text.setText("Aucun résultat trouvé.")
                        return
                    
                    output = f"Trouvé {len(recordings)} résultat(s):\n\n"
                    for i, rec in enumerate(recordings, 1):
                        rec_title = rec.get('title', 'N/A')
                        artists = ', '.join([a.get('name', '') for a in rec.get('artist-credit', [])])
                        releases = rec.get('releases', [])
                        album = releases[0].get('title', 'N/A') if releases else 'N/A'
                        
                        output += f"{i}. {rec_title}\n"
                        output += f"   Artiste(s): {artists}\n"
                        output += f"   Album: {album}\n"
                        output += f"   ID: {rec.get('id', 'N/A')}\n\n"
                    
                    result_text.setText(output)
                else:
                    result_text.setText(f"Erreur API: {response.status_code}")
            
            except Exception as e:
                result_text.setText(f"Erreur lors de la recherche: {str(e)}\n\nAssurez-vous que 'requests' est installé:\npip install requests")
        
        btn_search.clicked.connect(perform_search)
        dialog.exec()

    def download_cover_online(self):
        """Télécharger une pochette d'album depuis Internet.
        
        Cette méthode permet de :
        - Rechercher une pochette via MusicBrainz + Cover Art Archive
        - Afficher un aperçu de la pochette trouvée (300x300 pixels)
        - Permettre à l'utilisateur de valider visuellement
        - Enregistrer la pochette dans le dossier de l'album comme "cover.jpg"
        - Rafraîchir automatiquement l'affichage
        
        Processus :
        1. Recherche du release_id via MusicBrainz
        2. Téléchargement de la pochette via Cover Art Archive
        3. Validation visuelle par l'utilisateur
        4. Sauvegarde locale
        
        Nécessite la bibliothèque 'requests' pour les appels HTTP.
        """
        item = self.playlist_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Avertissement", "Aucune musique sélectionnée.")
            return
        
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "Erreur", "Fichier introuvable.")
            return
        
        # Récupérer artiste et album pour la recherche
        try:
            if mutagen_available:
                if path.lower().endswith(".mp3"):
                    f = MP3(path)
                    artist = f.tags.get("TPE1").text[0] if f.tags and "TPE1" in f.tags else ""
                    album = f.tags.get("TALB").text[0] if f.tags and "TALB" in f.tags else ""
                else:
                    f = FLAC(path)
                    artist = f.get("artist", [""])[0]
                    album = f.get("album", [""])[0]
            else:
                artist = album = ""
        except:
            artist = album = ""
        
        # Créer le dialogue
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("Télécharger pochette en ligne")
        dialog.resize(600, 500)
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        artist_edit = QLineEdit(artist)
        album_edit = QLineEdit(album)
        form.addRow("Artiste:", artist_edit)
        form.addRow("Album:", album_edit)
        layout.addLayout(form)
        
        btn_search = QPushButton("Rechercher pochette")
        layout.addWidget(btn_search)
        
        preview_label = QLabel("Aperçu de la pochette apparaîtra ici")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setFixedSize(300, 300)
        preview_label.setStyleSheet("border: 1px solid #555; background: #1a1a1a;")
        layout.addWidget(preview_label, alignment=Qt.AlignCenter)
        
        btn_row = QHBoxLayout()
        btn_save = QPushButton("Enregistrer dans le dossier")
        btn_save.setEnabled(False)
        btn_cancel = QPushButton("Annuler")
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
        
        btn_cancel.clicked.connect(dialog.reject)
        
        # Utiliser une liste pour stocker l'image dans la closure
        downloaded_image_data = [None]
        
        def search_cover():
            """Fonction interne pour rechercher et télécharger la pochette."""
            preview_label.setText("Recherche en cours...")
            artist_q = artist_edit.text().strip()
            album_q = album_edit.text().strip()
            
            if not artist_q or not album_q:
                QMessageBox.warning(dialog, "Avertissement", "Veuillez entrer l'artiste et l'album.")
                preview_label.setText("Aperçu de la pochette apparaîtra ici")
                return
            
            try:
                import requests
                # Utilisation de Cover Art Archive via MusicBrainz
                query = f"artist:{artist_q} AND release:{album_q}"
                url = f"https://musicbrainz.org/ws/2/release/?query={query}&fmt=json&limit=1"
                
                response = requests.get(url, headers={'User-Agent': 'MusicManager/1.0'}, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    releases = data.get('releases', [])
                    
                    if not releases:
                        preview_label.setText("Aucune pochette trouvée")
                        return
                    
                    release_id = releases[0].get('id')
                    cover_url = f"https://coverartarchive.org/release/{release_id}/front-250"
                    
                    cover_response = requests.get(cover_url, timeout=10)
                    
                    if cover_response.status_code == 200:
                        downloaded_image_data[0] = cover_response.content
                        pixmap = qpix_from_bytes(cover_response.content, max_size=(300, 300))
                        preview_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        btn_save.setEnabled(True)
                    else:
                        preview_label.setText("Pochette non disponible")
                else:
                    preview_label.setText(f"Erreur API: {response.status_code}")
            
            except Exception as e:
                preview_label.setText(f"Erreur: {str(e)[:50]}")
                QMessageBox.warning(dialog, "Erreur", f"Erreur lors de la recherche:\n{str(e)}\n\nAssurez-vous que 'requests' est installé.")
        
        def save_cover():
            """Fonction interne pour sauvegarder la pochette téléchargée."""
            if not downloaded_image_data[0]:
                return
            
            folder = Path(path).parent
            save_path = folder / "cover.jpg"
            
            try:
                with open(save_path, "wb") as f:
                    f.write(downloaded_image_data[0])
                
                QMessageBox.information(dialog, "Succès", f"Pochette enregistrée :\n{save_path}")
                # Rafraîchir l'affichage
                self.show_metadata_for_path(path)
                dialog.accept()
            
            except Exception as e:
                QMessageBox.critical(dialog, "Erreur", f"Impossible d'enregistrer la pochette : {e}")
        
        btn_search.clicked.connect(search_cover)
        btn_save.clicked.connect(save_cover)
        
        dialog.exec()



# Enhancements (MIME check, auto-save playlist, XSPF online validation, drag&drop)
# These are appended as non-invasive monkey-patches so original code remains unchanged.

import threading

def _validate_xspf_online(filepath: str) -> bool:
    print("DEBUG: Tente de valider le fichier XSPF en ligne...")
    
    try:
        import requests
    except ImportError:
        print("ERREUR CRITIQUE: Le module 'requests' n'est pas installé.")
        return False
        
    try:
        with open(filepath, "rb") as f:
            files = {'file': (Path(filepath).name, f, 'application/xspf+xml')}
            
            # Utilisation d'un timeout plus long pour éviter les échecs rapides sur un réseau lent
            r = requests.post("https://validator.xspf.org/validate", files=files, timeout=30)
            
            if r.status_code == 200:
                print("DEBUG: Validation en ligne réussie (Code 200).")
                return True
            else:
                print(f"DEBUG: Validation en ligne ÉCHOUÉE. Code de statut HTTP: {r.status_code}")
                # Vous pouvez inspecter r.text pour voir le message d'erreur du validateur ici si nécessaire
                return False
                
    except requests.exceptions.Timeout:
        print("ERREUR: Le délai de connexion (Timeout) est dépassé pour la validation en ligne.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"ERREUR RÉSEAU/REQUÊTE: Une erreur s'est produite lors de la connexion. Détails: {e}")
        return False
    except Exception as e:
        print(f"ERREUR INCONNUE lors de la validation. Détails: {e}")
        return False

# Pensez à ajouter 'import requests' au début du fichier si ce n'est pas déjà fait.

# Keep original methods to call them from wrappers
_orig_scanner_run = ScannerThread.run
_orig_on_scan_finished = MusicManagerMain._on_scan_finished
_orig_save_playlist = MusicManagerMain.save_playlist

def _enhanced_scanner_run(self):
	"""Replacement run: uses python-magic if present, else falls back to extension check."""
	self.status.emit("Lancement du scan (vérification MIME)...")
	found = []
	all_paths = []
	for root, _, files in os.walk(self.folder):
		for name in files:
			all_paths.append(os.path.join(root, name))

	total = len(all_paths) if all_paths else 1
	checked = 0

	# try to import python-magic
	magic_available = False
	try:
		import magic as _magic  # type: ignore
		magic_available = True
	except Exception:
		magic_available = False

	for full in all_paths:
		if not getattr(self, "_running", True):
			break
		checked += 1
		accept = False
		try:
			if magic_available:
				try:
					mtype = _magic.from_file(full, mime=True)
					if isinstance(mtype, str) and mtype.startswith("audio/"):
						accept = True
				except Exception:
					accept = False
			if not accept:
				# fallback to extension check
				if full.lower().endswith((".mp3", ".flac")):
					accept = True
		except Exception:
			accept = full.lower().endswith((".mp3", ".flac"))

		if accept:
			found.append(full)
			try:
				self.file_found.emit(full)
			except Exception:
				pass

		try:
			self.progress.emit(int(checked / total * 100))
		except Exception:
			pass

		# keep a small sleep to avoid UI spin; preserve original behaviour
		time.sleep(0.01)

	try:
		self.finished.emit(found)
		self.status.emit(f"Scan terminé — {len(found)} fichier(s).")
	except Exception:
		pass

# attach enhanced run
ScannerThread.run = _enhanced_scanner_run

def _write_playlist_fallback(pl, filename: str):
	"""Write a simple XSPF for a playlist-like object."""
	from xml.etree import ElementTree as ET
	root = ET.Element("playlist", version="1", xmlns="http://xspf.org/ns/0/")
	title_el = ET.SubElement(root, "title"); title_el.text = getattr(pl, "name", Path(filename).stem)
	tl = ET.SubElement(root, "trackList")
	for t in getattr(pl, "tracks", []):
		p = t.path if hasattr(t, "path") else t
		tr_el = ET.SubElement(tl, "track")
		loc = ET.SubElement(tr_el, "location"); loc.text = f"file://{p}"
		try:
			if getattr(t, "title", None): ET.SubElement(tr_el, "title").text = t.title
			if getattr(t, "artist", None): ET.SubElement(tr_el, "creator").text = t.artist
			if getattr(t, "album", None): ET.SubElement(tr_el, "album").text = t.album
			if getattr(t, "duration", None): ET.SubElement(tr_el, "duration").text = str(t.duration)
		except Exception:
			pass
	tree = ET.ElementTree(root)
	try:
		ET.indent(tree, space="  ", level=0)
	except Exception:
		pass
	tree.write(filename, encoding="utf-8", xml_declaration=True)

def _autosave_playlist_default(self, files: List[str]):
    """Auto-save playlist_default.xspf in scanned folder after scan finishes."""
    try:
        folder = Path(self.folder_input.text().strip())
        if not folder or not files:
            return
        out = folder / "playlist_default.xspf"
        # prefer project writer if available
        try:
            if write_xspf and hasattr(self.playlist, "tracks"):
                try:
                    write_xspf(self.playlist, str(out))
                except Exception:
                    _write_playlist_fallback(self.playlist, str(out))
            else:
                _write_playlist_fallback(self.playlist, str(out))
            
            # Mise à jour directe car nous sommes encore dans le thread principal ici (avant le threading.Thread)
            self.status.showMessage(f"Playlist par défaut enregistrée: {out}", 8000)
        except Exception as e:
            self.status.showMessage(f"Échec sauvegarde playlist par défaut: {e}", 8000)

        # --- CORRECTION DU CRASH DE THREADING ICI ---
        # Nous devons utiliser un Signal pour communiquer du Thread -> GUI
        from PySide6.QtCore import QObject, Signal

        class WorkerSignal(QObject):
            message = Signal(str, int)

        # Créer le signaleur et le connecter à la barre de statut
        self._worker_signal = WorkerSignal()
        self._worker_signal.message.connect(self.status.showMessage)

        # attempt online validate (non-blocking) inside a thread
        def _validate_and_notify(path):
            # Cette fonction tourne en arrière-plan
            valid = _validate_xspf_online(str(path))
            if valid:
                # Émettre un signal (Thread-Safe) au lieu de toucher à self.status directement
                self._worker_signal.message.emit("Playlist par défaut validée en ligne", 6000)
            else:
                self._worker_signal.message.emit("Validation en ligne indisponible ou invalide", 6000)

        th = threading.Thread(target=_validate_and_notify, args=(out,), daemon=True)
        th.start()

    except Exception:
        pass

def _enhanced_on_scan_finished(self, files: List[str]):
	"""Wrapper around original _on_scan_finished: call original then autosave default playlist."""
	# call original handler (if exists)
	try:
		_orig_on_scan_finished(self, files)
	except Exception:
		# fallback: set internal state similarly
		try:
			self.found_files = files
			self.scan_progress.setValue(100)
			self.status.showMessage(f"Scan terminé — {len(files)} fichier(s) trouvé(s).")
		except Exception:
			pass
	# Auto-save playlist_default
	try:
		_autosave_playlist_default(self, files)
	except Exception:
		pass

# patch method
MusicManagerMain._on_scan_finished = _enhanced_on_scan_finished

def _enhanced_save_playlist(self):
	"""Wrapper: call original save_playlist, then offer online validation for the saved file."""
	# We call original implementation which opens file dialog and saves.
	try:
		_orig_save_playlist(self)
	except Exception as e:
		# propagate original error behaviour
		raise
	# Ask user to validate (user selects file to validate)
	reply = QMessageBox.question(self, "Validation XSPF", "Voulez-vous valider la playlist via validator.xspf.org ?", QMessageBox.Yes | QMessageBox.No)
	if reply == QMessageBox.Yes:
		# ask for file to validate (preselect home)
		fpath, _ = QFileDialog.getOpenFileName(self, "Sélectionner le fichier XSPF à valider", str(Path.home()), "XSPF files (*.xspf)")
		if fpath:
			ok = _validate_xspf_online(fpath)
			if ok:
				QMessageBox.information(self, "Validation", "Le validateur a répondu OK (HTTP 200).")
			else:
				QMessageBox.warning(self, "Validation", "Validation en ligne échouée ou requête indisponible.")

# patch save
MusicManagerMain.save_playlist = _enhanced_save_playlist

def _add_file_to_playlist(self, path: str):
	"""Add a single file to playlist and UI (used by drag & drop)."""
	try:
		if not path or not Path(path).exists():
			return
		# prevent duplicates by path
		for i in range(self.playlist_widget.count()):
			item = self.playlist_widget.item(i)
			if item and item.data(Qt.ItemDataRole.UserRole) == path:
				# already present
				return
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
		# add to model
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
		item = QListWidgetItem(Path(path).name)
		item.setData(Qt.ItemDataRole.UserRole, path)
		self.playlist_widget.addItem(item)
		# status
		try:
			self.status.showMessage(f"Fichier ajouté à la playlist: {Path(path).name}", 4000)
		except Exception:
			pass
	except Exception:
		pass

# attach method to class
MusicManagerMain.add_file_to_playlist = _add_file_to_playlist

def _setup_playlist_dnd_for_instance(win: MusicManagerMain):
	"""Configure drop handling on the playlist widget for an instance."""
	try:
		w = win.playlist_widget
		w.setAcceptDrops(True)
		# define dropEvent bound to the instance (captures win)
		def _dropEvent(event):
			if event.mimeData().hasUrls():
				added = 0
				for url in event.mimeData().urls():
					try:
						path = url.toLocalFile()
					except Exception:
						path = str(url.toString())
					if path and Path(path).suffix.lower() in (".mp3", ".flac"):
						try:
							win.add_file_to_playlist(path)
							added += 1
						except Exception:
							pass
				if added:
					try:
						win.status.showMessage(f"{added} fichier(s) déposé(s) dans la playlist", 4000)
					except Exception:
						pass
				event.acceptProposedAction()
			else:
				event.ignore()
		# bind to widget
		w.dropEvent = _dropEvent
		# visual feedback via stylesheet tweak is left to UI designer
	except Exception:
		pass

def enhance_gui_instance(win: MusicManagerMain):
	"""Apply instance-level enhancements (called once after window creation)."""
	try:
		_setup_playlist_dnd_for_instance(win)
		# Optionally show which backend is used (library vs fallback) in status bar
		try:
			used = "library" if use_project_library else "fallback"
			backends = []
			if qt_multimedia_available: backends.append("QtMultimedia")
			if pygame_available: backends.append("pygame")
			if mutagen_available: backends.append("mutagen")
			win.status.showMessage(f"Backend: {used} — Audio: {', '.join(backends)}", 6000)
		except Exception:
			pass
	except Exception:
		pass

# ensure enhance_gui is available to main
def _call_enhance_later(win):
	QTimer.singleShot(400, lambda: enhance_gui_instance(win))


# Inject call into main() run (non-intrusive)
# We update main to schedule our enhancement after the window is shown.

def main():
	"""Point d'entrée de l'application GUI.

	Initialise QApplication, crée la fenêtre principale et lance la boucle d'événement Qt.
	Conserver simple pour permettre l'appel direct (python music_manager_gui.py).
	"""
	app = QApplication(sys.argv)
	win = MusicManagerMain()
	win.show()
	# schedule enhancements (drag&drop on playlist, status message, etc.)
	_call_enhance_later(win)
	from PySide6.QtCore import QTimer
	def _print_sizes():
		anim = getattr(win, "_anim_widget", None)
		container = getattr(win, "_anim_container", None)
		print("DEBUG LAYOUT ► anim:", anim.size() if anim else "missing",
			  "container:", container.size() if container else "missing",
			  "playlist viewport:", win.playlist_widget.viewport().size())
	QTimer.singleShot(300, _print_sizes)
	sys.exit(app.exec())

if __name__ == "__main__":
	# Exécution directe du script : lance l'application GUI.
	main()
