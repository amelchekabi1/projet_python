# -*- coding: utf-8 -*-
"""
playlist.py

Gestion des playlists et des pistes musicales.

Ce module fournit :

- une classe :class:`Track` représentant une piste audio (chemin, titre,
  artiste, album, durée, etc.), compatible avec le format XSPF et le GUI ;
- une classe :class:`Playlist` représentant une liste ordonnée de pistes ;
- des fonctions utilitaires pour créer une playlist à partir de fichiers
  et pour charger une playlist depuis un fichier XSPF.

Il est utilisé à la fois par l'interface graphique (GUI) et par la ligne
de commande (CLI).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List
import os
import xml.etree.ElementTree as ET


class Track:
    """
    Représente une piste audio dans une playlist.

    Une piste contient les informations principales d'un morceau :
    chemin de fichier, titre, artiste, album, durée, numéro de piste.
    Les attributs ``location`` et ``creator`` sont ajoutés pour
    faciliter la compatibilité avec le format XSPF et certains usages
    côté GUI.
    """

    def __init__(
        self,
        path: str,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        duration: Optional[int] = None,
        track_number: Optional[str] = None,
    ):
        """
        Initialise une piste audio.

        Args:
            path (str): Chemin vers le fichier audio sur le disque.
            title (str | None): Titre du morceau. Si None, le nom de
                fichier (sans extension) est utilisé.
            artist (str | None): Nom de l'artiste. Par défaut ``"Inconnu"``.
            album (str | None): Nom de l'album. Par défaut ``"Album inconnu"``.
            duration (int | None): Durée en secondes.
            track_number (str | None): Numéro de piste au sein de l'album.
        """
        self.path = str(Path(path).resolve())
        self.title = title or Path(path).stem
        self.artist = artist or "Inconnu"
        self.album = album or "Album inconnu"
        self.duration = duration  # en secondes
        self.track_number = track_number

        # Attributs pour compatibilité XSPF
        self.location = f"file://{Path(self.path).absolute()}"
        # XSPF utilise 'creator' pour l'artiste
        self.creator = self.artist

    @classmethod
    def from_audiofile(cls, audio_file) -> "Track":
        """
        Crée un objet Track à partir d'une instance de AudioFile.

        Les métadonnées sont lues via :meth:`AudioFile.read_metadata`
        puis injectées dans le constructeur de :class:`Track`.

        Args:
            audio_file: Instance d'une sous-classe de :class:`AudioFile`
                (MP3AudioFile, FLACAudioFile, etc.).

        Returns:
            Track: Nouvelle piste construite à partir des métadonnées
            du fichier audio.
        """
        metadata = audio_file.read_metadata()

        return cls(
            path=str(audio_file.path),
            title=metadata.title,
            artist=metadata.artist,
            album=metadata.album,
            duration=metadata.duration_sec,
            track_number=metadata.track_no,
        )

    def display(self) -> str:
        """
        Retourne une représentation courte et lisible de la piste.

        Returns:
            str: Chaîne de la forme ``"Artiste — Titre"``.
        """
        return f"{self.artist} — {self.title}"

    def to_dict(self) -> dict:
        """
        Convertit la piste en dictionnaire.

        Utile pour la sérialisation ou pour échange de données entre
        différentes couches (GUI, CLI, etc.).

        Returns:
            dict: Dictionnaire contenant les principales informations
            de la piste (chemin, titre, artiste, album, durée, etc.).
        """
        return {
            "path": self.path,
            "location": self.location,
            "title": self.title,
            "artist": self.artist,
            "creator": self.creator,
            "album": self.album,
            "duration": self.duration,
            "track_number": self.track_number,
        }

    def __str__(self) -> str:
        """
        Retourne une représentation détaillée de la piste en texte.

        Returns:
            str: Représentation textuelle avec titre, artiste et durée.
        """
        duration_str = f"{self.duration}s" if self.duration else "?"
        return f"Track({self.title} - {self.artist} [{duration_str}])"

    def __repr__(self) -> str:
        """
        Retourne une représentation technique de la piste.

        Returns:
            str: Chaîne présentant le chemin et le titre.
        """
        return f"Track(path='{self.path}', title='{self.title}')"


class Playlist:
    """
    Représente une playlist de pistes audio.

    La playlist conserve un nom (utilisé également comme titre pour XSPF)
    et une liste ordonnée de :class:`Track`. Elle offre des méthodes pour
    ajouter, supprimer, déplacer des pistes, calculer la durée totale,
    itérer, etc.
    """

    def __init__(self, name: str = "Nouvelle Playlist"):
        """
        Initialise une playlist.

        Args:
            name (str): Nom de la playlist (utilisé aussi comme titre
                pour certaines intégrations XSPF).
        """
        self.name = name
        # Pour compatibilité XSPF : certains writers attendent un attribut title
        self.title = name
        self.tracks: List[Track] = []

    def add_track(self, track: Track) -> None:
        """
        Ajoute une piste à la playlist.

        Args:
            track (Track): Piste à ajouter.

        Raises:
            TypeError: Si l'objet fourni n'est pas une instance de Track.
        """
        if not isinstance(track, Track):
            raise TypeError("track doit être une instance de Track")
        self.tracks.append(track)

    def remove_track(self, index: int) -> Optional[Track]:
        """
        Supprime une piste par son index.

        Args:
            index (int): Index de la piste à supprimer (0-based).

        Returns:
            Track | None: La piste supprimée si l'index est valide, sinon None.
        """
        if 0 <= index < len(self.tracks):
            return self.tracks.pop(index)
        return None

    def move_track(self, from_index: int, to_index: int) -> bool:
        """
        Déplace une piste d'une position à une autre dans la playlist.

        Args:
            from_index (int): Position actuelle de la piste.
            to_index (int): Nouvelle position souhaitée.

        Returns:
            bool: True si le déplacement a réussi, False si les indices
            sont hors bornes.
        """
        if not (0 <= from_index < len(self.tracks) and 0 <= to_index < len(self.tracks)):
            return False

        track = self.tracks.pop(from_index)
        self.tracks.insert(to_index, track)
        return True

    def clear(self) -> None:
        """
        Vide complètement la playlist.

        Supprime toutes les pistes.
        """
        self.tracks.clear()

    def get_track(self, index: int) -> Optional[Track]:
        """
        Récupère une piste par son index.

        Args:
            index (int): Index de la piste (0-based).

        Returns:
            Track | None: La piste correspondante si l'index est valide,
            None sinon.
        """
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def total_duration(self) -> int:
        """
        Calcule la durée totale de la playlist en secondes.

        Seules les pistes dont la durée est renseignée sont prises en
        compte.

        Returns:
            int: Durée totale en secondes (somme des durées des pistes).
        """
        return sum(track.duration for track in self.tracks if track.duration)

    def __len__(self) -> int:
        """
        Retourne le nombre de pistes dans la playlist.

        Returns:
            int: Longueur de la playlist.
        """
        return len(self.tracks)

    def __iter__(self):
        """
        Permet d'itérer directement sur les pistes de la playlist.

        Returns:
            iterator: Itérateur sur la liste des :class:`Track`.
        """
        return iter(self.tracks)

    def __getitem__(self, index: int) -> Track:
        """
        Permet l'accès indexé aux pistes de la playlist.

        Args:
            index (int): Position de la piste.

        Returns:
            Track: Piste à la position donnée.
        """
        return self.tracks[index]

    def __str__(self) -> str:
        """
        Retourne une représentation textuelle résumée de la playlist.

        Returns:
            str: Chaîne indiquant le nom, le nombre de pistes, et la
            durée totale en minutes.
        """
        duration_min = self.total_duration() // 60
        return f"Playlist('{self.name}', {len(self.tracks)} pistes, {duration_min}min)"

    def __repr__(self) -> str:
        """
        Retourne une représentation technique de la playlist.

        Returns:
            str: Chaîne indiquant le nom et le nombre de pistes.
        """
        return f"Playlist(name='{self.name}', tracks={len(self.tracks)})"


# Fonctions utilitaires

def create_playlist_from_files(files: List[str], name: str = "Nouvelle Playlist") -> Playlist:
    """
    Crée une playlist à partir d'une liste de chemins de fichiers.

    Cette fonction tente d'abord d'utiliser :class:`AudioFile` (module
    ``library.audiofile``) pour extraire des métadonnées complètes.
    En cas d'échec (erreur de lecture, format non supporté, etc.), une
    piste basique est tout de même créée à partir du chemin.

    Args:
        files (list[str]): Liste de chemins de fichiers audio.
        name (str): Nom à attribuer à la playlist.

    Returns:
        Playlist: Nouvelle playlist remplie avec des objets :class:`Track`.
    """
    playlist = Playlist(name)

    # Essayer d'utiliser AudioFile pour extraire les métadonnées
    try:
        from library.audiofile import AudioFile

        for file_path in files:
            try:
                audio = AudioFile.from_path(file_path)
                track = Track.from_audiofile(audio)
                playlist.add_track(track)
            except Exception:
                # Fallback : créer un track basique si la lecture échoue
                track = Track(file_path)
                playlist.add_track(track)
    except ImportError:
        # Si AudioFile n'est pas disponible, créer des tracks basiques
        for file_path in files:
            track = Track(file_path)
            playlist.add_track(track)

    return playlist


def load_playlist_from_xspf(xspf_path: str) -> List[Track]:
    """
    Charge une playlist depuis un fichier XSPF.

    Cette fonction parse un fichier XSPF (XML), en extrait les éléments
    ``<track>`` et crée une liste de :class:`Track` à partir des champs
    XSPF standard (``location``, ``title``, ``creator``, ``album``).

    Le chemin de fichier est reconstruit à partir de l'URI ``file://`` en
    gérant à la fois les cas Linux/WSL et Windows.

    Args:
        xspf_path (str): Chemin vers le fichier XSPF à lire.

    Returns:
        list[Track]: Liste de pistes représentant le contenu de la
        playlist XSPF.
    """
    from urllib.parse import unquote, urlparse

    xspf_path = Path(xspf_path)
    tree = ET.parse(xspf_path)
    root = tree.getroot()

    tracks_list: List[Track] = []

    for track_elem in root.findall(".//{*}track"):
        loc_elem = track_elem.find("{*}location")
        title_elem = track_elem.find("{*}title")
        artist_elem = track_elem.find("{*}creator")
        album_elem = track_elem.find("{*}album")

        if loc_elem is None or not loc_elem.text:
            continue

        location = loc_elem.text.strip()

        # Conversion de l'URI XSPF -> chemin local
        if location.startswith("file://"):
            parsed = urlparse(location)

            # Cas Linux / WSL : file:///home/...
            raw_path = parsed.path or ""

            # Cas Windows : file://C:\Users\... (dans netloc)
            if not raw_path and parsed.netloc:
                raw_path = parsed.netloc

            path = unquote(raw_path)

            # Sous Windows, corriger /C:/Users/... -> C:/Users/...
            if os.name == "nt" and path.startswith("/") and ":" in path:
                path = path[1:]
        else:
            # Pas de préfixe file:// → on utilise tel quel
            path = location

        track = Track(
            path=path,
            title=title_elem.text if title_elem is not None else None,
            artist=artist_elem.text if artist_elem is not None else None,
            album=album_elem.text if album_elem is not None else None,
        )
        tracks_list.append(track)

    return tracks_list


# Test unitaire simple
if __name__ == "__main__":
    # Test 1 : Créer une playlist manuellement
    pl = Playlist("Ma Playlist Test")

    track1 = Track(
        "/music/song1.mp3",
        title="Chanson 1",
        artist="Artiste 1",
        album="Album 1",
        duration=180,
    )

    track2 = Track(
        "/music/song2.flac",
        title="Chanson 2",
        artist="Artiste 2",
        album="Album 2",
        duration=240,
    )

    pl.add_track(track1)
    pl.add_track(track2)

    print(pl)
    print(f"Durée totale: {pl.total_duration()}s")

    for i, track in enumerate(pl):
        print(f"  {i+1}. {track}")

    # Test 2 : Supprimer et déplacer
    print("\nTest déplacement...")
    pl.move_track(1, 0)
    for i, track in enumerate(pl):
        print(f"  {i+1}. {track}")

    print("\n✅ Tests réussis !")
