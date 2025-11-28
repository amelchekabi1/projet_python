# -*- coding: utf-8 -*-
"""
playlist.py
Gestion des playlists et des pistes musicales.
Compatible avec le GUI et le CLI.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


class Track:
    """
    Représente une piste audio dans une playlist.
    Compatible avec XSPF et le GUI.
    """
    
    def __init__(self, 
                 path: str,
                 title: Optional[str] = None,
                 artist: Optional[str] = None,
                 album: Optional[str] = None,
                 duration: Optional[int] = None,
                 track_number: Optional[str] = None):
        """
        Initialise une piste.
        
        Args:
            path: Chemin vers le fichier audio
            title: Titre du morceau
            artist: Artiste
            album: Album
            duration: Durée en secondes
            track_number: Numéro de piste
        """
        self.path = str(Path(path).resolve())
        self.title = title or Path(path).stem
        self.artist = artist or "Inconnu"
        self.album = album or "Album inconnu"
        self.duration = duration  # en secondes
        self.track_number = track_number
        
        # Attributs pour compatibilité XSPF
        self.location = f"file://{Path(self.path).absolute()}"
        self.creator = self.artist  # XSPF utilise 'creator' pour l'artiste
    
    @classmethod
    def from_audiofile(cls, audio_file) -> Track:
        """
        Crée un Track à partir d'un objet AudioFile.
        
        Args:
            audio_file: Instance de AudioFile
            
        Returns:
            Track: Nouvelle instance
        """
        metadata = audio_file.read_metadata()
        
        return cls(
            path=str(audio_file.path),
            title=metadata.title,
            artist=metadata.artist,
            album=metadata.album,
            duration=metadata.duration_sec,
            track_number=metadata.track_no
        )
    
    def display(self) -> str:
        """Retourne une représentation lisible pour l'affichage."""
        return f"{self.artist} — {self.title}"
    
    def to_dict(self) -> dict:
        """Retourne les données sous forme de dictionnaire."""
        return {
            "path": self.path,
            "location": self.location,
            "title": self.title,
            "artist": self.artist,
            "creator": self.creator,
            "album": self.album,
            "duration": self.duration,
            "track_number": self.track_number
        }
    
    def __str__(self) -> str:
        duration_str = f"{self.duration}s" if self.duration else "?"
        return f"Track({self.title} - {self.artist} [{duration_str}])"
    
    def __repr__(self) -> str:
        return f"Track(path='{self.path}', title='{self.title}')"


class Playlist:
    """
    Représente une playlist de pistes audio.
    Compatible avec XSPF writer et le GUI.
    """
    
    def __init__(self, name: str = "Nouvelle Playlist"):
        """
        Initialise une playlist.
        
        Args:
            name: Nom de la playlist
        """
        self.name = name
        self.title = name  # Pour compatibilité XSPF
        self.tracks: List[Track] = []
    
    def add_track(self, track: Track) -> None:
        """
        Ajoute une piste à la playlist.
        
        Args:
            track: Piste à ajouter
        """
        if not isinstance(track, Track):
            raise TypeError("track doit être une instance de Track")
        self.tracks.append(track)
    
    def remove_track(self, index: int) -> Optional[Track]:
        """
        Supprime une piste par son index.
        
        Args:
            index: Index de la piste à supprimer
            
        Returns:
            Track supprimé ou None
        """
        if 0 <= index < len(self.tracks):
            return self.tracks.pop(index)
        return None
    
    def move_track(self, from_index: int, to_index: int) -> bool:
        """
        Déplace une piste dans la playlist.
        
        Args:
            from_index: Position actuelle
            to_index: Nouvelle position
            
        Returns:
            bool: True si succès
        """
        if not (0 <= from_index < len(self.tracks) and 0 <= to_index < len(self.tracks)):
            return False
        
        track = self.tracks.pop(from_index)
        self.tracks.insert(to_index, track)
        return True
    
    def clear(self) -> None:
        """Vide la playlist."""
        self.tracks.clear()
    
    def get_track(self, index: int) -> Optional[Track]:
        """
        Récupère une piste par son index.
        
        Args:
            index: Index de la piste
            
        Returns:
            Track ou None
        """
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None
    
    def total_duration(self) -> int:
        """
        Calcule la durée totale de la playlist en secondes.
        
        Returns:
            int: Durée totale en secondes
        """
        return sum(track.duration for track in self.tracks if track.duration)
    
    def __len__(self) -> int:
        """Retourne le nombre de pistes."""
        return len(self.tracks)
    
    def __iter__(self):
        """Permet d'itérer sur les pistes."""
        return iter(self.tracks)
    
    def __getitem__(self, index: int) -> Track:
        """Permet l'accès par index."""
        return self.tracks[index]
    
    def __str__(self) -> str:
        duration_min = self.total_duration() // 60
        return f"Playlist('{self.name}', {len(self.tracks)} pistes, {duration_min}min)"
    
    def __repr__(self) -> str:
        return f"Playlist(name='{self.name}', tracks={len(self.tracks)})"


# Fonctions utilitaires

def create_playlist_from_files(files: List[str], name: str = "Nouvelle Playlist") -> Playlist:
    """
    Crée une playlist à partir d'une liste de fichiers.
    
    Args:
        files: Liste de chemins de fichiers
        name: Nom de la playlist
        
    Returns:
        Playlist: Nouvelle playlist
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
            except Exception as e:
                # Fallback : créer un track basique
                track = Track(file_path)
                playlist.add_track(track)
    except ImportError:
        # Si AudioFile n'est pas disponible, créer des tracks basiques
        for file_path in files:
            track = Track(file_path)
            playlist.add_track(track)
    
    return playlist


def load_playlist_from_xspf(xspf_path: str) -> Playlist:
    """
    Charge une playlist depuis un fichier XSPF.
    
    Args:
        xspf_path: Chemin vers le fichier XSPF
        
    Returns:
        Playlist: Playlist chargée
        
    Note: Implémentation future
    """
    import xml.etree.ElementTree as ET
    from urllib.parse import unquote, urlparse
    
    tree = ET.parse(xspf_path)
    root = tree.getroot()
    
    # Namespace XSPF
    ns = {'xspf': 'http://xspf.org/ns/0/'}
    
    # Récupérer le titre
    title_elem = root.find('xspf:title', ns)
    name = title_elem.text if title_elem is not None else "Playlist importée"
    
    playlist = Playlist(name)
    
    # Récupérer les tracks
    tracklist = root.find('xspf:trackList', ns)
    if tracklist is not None:
        for track_elem in tracklist.findall('xspf:track', ns):
            # Location
            loc_elem = track_elem.find('xspf:location', ns)
            if loc_elem is None:
                continue
            
            # Convertir file:// URL en chemin
            location = loc_elem.text
            if location.startswith('file://'):
                path = unquote(urlparse(location).path)
                # Sur Windows, enlever le / initial
                if path.startswith('/') and ':' in path:
                    path = path[1:]
            else:
                path = location
            
            # Métadonnées
            title_elem = track_elem.find('xspf:title', ns)
            title = title_elem.text if title_elem is not None else None
            
            creator_elem = track_elem.find('xspf:creator', ns)
            artist = creator_elem.text if creator_elem is not None else None
            
            album_elem = track_elem.find('xspf:album', ns)
            album = album_elem.text if album_elem is not None else None
            
            duration_elem = track_elem.find('xspf:duration', ns)
            duration = int(duration_elem.text) // 1000 if duration_elem is not None else None
            
            # Créer le track
            track = Track(path, title=title, artist=artist, album=album, duration=duration)
            playlist.add_track(track)
    
    return playlist


# Test unitaire
if __name__ == "__main__":
    # Test 1 : Créer une playlist manuellement
    pl = Playlist("Ma Playlist Test")
    
    track1 = Track(
        "/music/song1.mp3",
        title="Chanson 1",
        artist="Artiste 1",
        album="Album 1",
        duration=180
    )
    
    track2 = Track(
        "/music/song2.flac",
        title="Chanson 2",
        artist="Artiste 2",
        album="Album 2",
        duration=240
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