# -*- coding: utf-8 -*-
"""
audiofile.py

Gestion des fichiers audio MP3/FLAC et extraction de métadonnées.

Ce module définit :

- une structure :class:`Metadata` pour transporter les métadonnées utiles ;
- une classe abstraite :class:`AudioFile` pour factoriser l'interface commune ;
- deux implémentations concrètes : :class:`MP3AudioFile` et :class:`FLACAudioFile`.

Les métadonnées sont lues et modifiées à l'aide de la bibliothèque
``mutagen`` (ID3 pour les MP3, Vorbis Comment pour les FLAC).
"""

from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

# mutagen gère de nombreux formats audio ; ici on utilise MP3 et FLAC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError


@dataclass
class Metadata:
    """
    Structure simple et typée pour transporter les métadonnées utiles.

    Cette structure regroupe les principaux champs présents dans les TAGS
    audio (ID3 pour MP3, Vorbis Comment pour FLAC) et permet de passer
    ces informations de manière compacte entre les différentes couches
    (CLI, GUI, etc.).
    """
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    track_no: Optional[str] = None
    duration_sec: Optional[int] = None
    year: Optional[str] = None
    genre: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'objet Metadata en dictionnaire.

        Returns:
            dict: Dictionnaire contenant les champs suivants :
            ``title``, ``artist``, ``album``, ``track_no``,
            ``duration_sec``, ``year``, ``genre``.
        """
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "track_no": self.track_no,
            "duration_sec": self.duration_sec,
            "year": self.year,
            "genre": self.genre,
        }


class AudioFile(ABC):
    """
    Classe abstraite de base pour représenter un fichier audio.

    Cette classe définit l'interface commune que doivent respecter les
    implémentations concrètes (MP3, FLAC, etc.) pour :

    - lire les métadonnées ;
    - mettre à jour les métadonnées ;
    - formater les informations pour affichage en console.

    Les classes concrètes :class:`MP3AudioFile` et :class:`FLACAudioFile`
    héritent de cette interface.
    """

    def __init__(self, path: str | Path):
        """
        Initialise un objet AudioFile à partir d'un chemin.

        Args:
            path (str | Path): Chemin du fichier audio.
        """
        self.path = Path(path)

    @abstractmethod
    def update_metadata(self,
                        title: Optional[str] = None,
                        artist: Optional[str] = None,
                        album: Optional[str] = None,
                        year: Optional[str] = None,
                        genre: Optional[str] = None,
                        track_no: Optional[str] = None) -> bool:
        """
        Met à jour les métadonnées persistantes du fichier audio.

        Les paramètres sont optionnels : si une valeur est None, le champ
        correspondant n'est pas modifié.

        Args:
            title (str | None): Nouveau titre.
            artist (str | None): Nouvel artiste.
            album (str | None): Nouvel album.
            year (str | None): Nouvelle année (chaîne brute).
            genre (str | None): Nouveau genre.
            track_no (str | None): Nouveau numéro de piste.

        Returns:
            bool: True si la sauvegarde s'est bien déroulée, False sinon.
        """
        raise NotImplementedError

    @abstractmethod
    def read_metadata(self) -> Metadata:
        """
        Lit les métadonnées du fichier audio.

        Returns:
            Metadata: Objet regroupant les informations lues dans les TAGS
            (titre, artiste, album, durée, etc.).
        """
        raise NotImplementedError

    def get_metadata_as_str(self) -> str:
        """
        Retourne une représentation textuelle des métadonnées.

        Principalement utilisée pour un affichage lisible en console (CLI).

        Returns:
            str: Chaîne multi-ligne avec les champs principaux des
            métadonnées (titre, artiste, album, année, etc.).
        """
        md = self.read_metadata().to_dict()
        lines = [
            f"Titre   : {md.get('title') or ''}",
            f"Artiste : {md.get('artist') or ''}",
            f"Album   : {md.get('album') or ''}",
            f"Piste # : {md.get('track_no') or ''}",
            f"Année   : {md.get('year') or ''}",
            f"Genre   : {md.get('genre') or ''}",
            f"Durée   : {md.get('duration_sec') or 0} s",
            f"Fichier : {self.path}",
        ]
        return "\n".join(lines)

    @staticmethod
    def from_path(path: str | Path) -> "AudioFile":
        """
        Fabrique l'implémentation concrète appropriée à partir de l'extension.

        Si l'extension est ``.mp3``, retourne un :class:`MP3AudioFile`.
        Si l'extension est ``.flac``, retourne un :class:`FLACAudioFile`.

        Args:
            path (str | Path): Chemin du fichier audio.

        Returns:
            AudioFile: Instance de la classe concrete correspondante.

        Raises:
            ValueError: Si le format n'est pas supporté (extension autre
                que ``.mp3`` ou ``.flac``).
        """
        p = Path(path)
        ext = p.suffix.lower()
        if ext == ".mp3":
            return MP3AudioFile(p)
        if ext == ".flac":
            return FLACAudioFile(p)
        # conforme au sujet : seuls MP3 et FLAC sont supportés ici
        raise ValueError(f"Format non supporté pour {p} (attendu .mp3 ou .flac)")


class MP3AudioFile(AudioFile):
    """
    Gestion des fichiers MP3 à l'aide des tags ID3.

    Cette classe utilise :mod:`mutagen.mp3` et les frames ID3 (TIT2, TPE1,
    TALB, TDRC, TCON, TRCK, etc.) pour lire et écrire les métadonnées.
    """

    def __init__(self, path: str | Path):
        """
        Initialise un objet MP3AudioFile et charge le conteneur mutagen.

        En cas d'absence de header ID3, le fichier MP3 reste tout de même
        chargé afin de pouvoir récupérer des informations comme la durée.

        Args:
            path (str | Path): Chemin du fichier MP3.
        """
        super().__init__(path)
        try:
            self.audio = MP3(self.path)
        except ID3NoHeaderError:
            # Fichier MP3 valide sans header ID3 : on recharge pour avoir la durée
            self.audio = MP3(self.path)

    def _get_id3_text(self, frame: str) -> Optional[str]:
        """
        Récupère la première valeur texte d'un frame ID3.

        Certains frames typiques sont par exemple :

        - ``"TIT2"`` : titre ;
        - ``"TPE1"`` : artiste ;
        - ``"TALB"`` : album ;
        - ``"TDRC"`` / ``"TYER"`` : date/année ;
        - ``"TCON"`` : genre ;
        - ``"TRCK"`` : numéro de piste.

        Args:
            frame (str): Nom du frame ID3 à lire.

        Returns:
            str | None: Texte du frame si présent, None sinon.
        """
        tag = self.audio.tags
        if not tag or frame not in tag:
            return None
        value = tag.get(frame)
        try:
            # mutagen normalise souvent en objets avec .text (liste)
            text_list = getattr(value, "text", None)
            if isinstance(text_list, list) and text_list:
                return str(text_list[0])
            return str(value)
        except Exception:
            return None

    def read_metadata(self) -> Metadata:
        """
        Lit les métadonnées d'un fichier MP3.

        Utilise les frames ID3 pour récupérer les champs principaux
        (titre, artiste, album, genre, numéro de piste, année) ainsi
        que la durée.

        Returns:
            Metadata: Métadonnées extraites du fichier MP3.
        """
        # Durée (en secondes entières)
        duration = None
        if self.audio and self.audio.info:
            duration = int(self.audio.info.length)

        # Champs ID3 courants
        title = self._get_id3_text("TIT2")
        artist = self._get_id3_text("TPE1")
        album = self._get_id3_text("TALB")
        year_raw = self._get_id3_text("TDRC") or self._get_id3_text("TYER")
        genre = self._get_id3_text("TCON")
        track_no = self._get_id3_text("TRCK")

        # Formater la date si nécessaire
        year = self._format_date(year_raw) if year_raw else None

        return Metadata(
            title=title,
            artist=artist,
            album=album,
            track_no=track_no,
            duration_sec=duration,
            year=year,
            genre=genre,
        )

    def update_metadata(self,
                        title: Optional[str] = None,
                        artist: Optional[str] = None,
                        album: Optional[str] = None,
                        year: Optional[str] = None,
                        genre: Optional[str] = None,
                        track_no: Optional[str] = None) -> bool:
        """
        Met à jour les métadonnées ID3 du fichier MP3.

        Pour chaque paramètre non None, le frame ID3 correspondant est
        mis à jour. Les tags sont créés si absents.

        Args:
            title (str | None): Nouveau titre (frame ``TIT2``).
            artist (str | None): Nouvel artiste (frame ``TPE1``).
            album (str | None): Nouvel album (frame ``TALB``).
            year (str | None): Nouvelle année (frame ``TDRC``).
            genre (str | None): Nouveau genre (frame ``TCON``).
            track_no (str | None): Nouveau n° de piste (frame ``TRCK``).

        Returns:
            bool: True si la sauvegarde a réussi, False en cas d'erreur.
        """
        from mutagen.id3 import TIT2, TPE1, TALB, TDRC, TCON, TRCK

        try:
            # Créer les tags si absents
            if not self.audio.tags:
                self.audio.add_tags()

            # Mettre à jour les champs fournis
            if title is not None:
                self.audio.tags["TIT2"] = TIT2(encoding=3, text=title)
            if artist is not None:
                self.audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
            if album is not None:
                self.audio.tags["TALB"] = TALB(encoding=3, text=album)
            if year is not None:
                self.audio.tags["TDRC"] = TDRC(encoding=3, text=str(year))
            if genre is not None:
                self.audio.tags["TCON"] = TCON(encoding=3, text=genre)
            if track_no is not None:
                self.audio.tags["TRCK"] = TRCK(encoding=3, text=str(track_no))

            # Sauvegarder
            self.audio.save()
            return True
        except Exception as e:
            print(f"Erreur lors de la mise à jour des tags MP3 : {e}")
            return False

    def _format_date(self, date_str: str) -> str:
        """
        Formate une date en provenance des tags ID3 vers un format lisible.

        Cette méthode gère quelques formats courants rencontrés dans les tags :

        - ``YYYYMMDD`` (ex: ``20180705``) → ``"05/07/2018"`` ;
        - ``YYYY-MM-DD`` (ex: ``2018-07-05``) → ``"05/07/2018"`` ;
        - ``YYYY`` seul (ex: ``2018``) → ``"2018"``.

        Si le format n'est pas reconnu, la valeur d'entrée est renvoyée telle quelle.

        Args:
            date_str (str): Date sous forme de chaîne.

        Returns:
            str: Date formatée en chaîne lisible, ou date brute si le
            format est inconnu.
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Format YYYYMMDD (ex: 20180705)
        if len(date_str) == 8 and date_str.isdigit():
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{day}/{month}/{year}"

        # Format YYYY-MM-DD (ex: 2018-07-05)
        elif "-" in date_str and len(date_str) == 10:
            parts = date_str.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"

        # Format YYYY seulement (ex: 2018)
        elif len(date_str) == 4 and date_str.isdigit():
            return date_str

        # Autre : retourner tel quel
        return date_str


class FLACAudioFile(AudioFile):
    """
    Gestion des fichiers FLAC à l'aide des tags Vorbis Comment.

    Cette classe utilise :mod:`mutagen.flac` et les champs texte Vorbis
    (TITLE, ARTIST, ALBUM, DATE, GENRE, TRACKNUMBER, etc.) pour lire
    et écrire les métadonnées.
    """

    def __init__(self, path: str | Path):
        """
        Initialise un objet FLACAudioFile et charge le conteneur mutagen.

        Args:
            path (str | Path): Chemin du fichier FLAC.
        """
        super().__init__(path)
        self.audio = FLAC(self.path)

    def _get_vorbis(self, key: str) -> Optional[str]:
        """
        Lit un champ texte Vorbis Comment.

        Dans les fichiers FLAC, les tags sont généralement stockés sous
        forme de listes de chaînes. Cette méthode renvoie la première
        valeur si elle existe.

        Args:
            key (str): Nom du champ Vorbis (par ex. ``"title"``,
                ``"artist"``, ``"album"``, ``"genre"``, etc.).

        Returns:
            str | None: Première valeur associée à la clé, ou None si
            le champ est absent.
        """
        try:
            values = self.audio.get(key, None)
            if not values:
                return None
            if isinstance(values, list) and values:
                return str(values[0])
            return str(values)
        except Exception:
            return None

    def read_metadata(self) -> Metadata:
        """
        Lit les métadonnées d'un fichier FLAC.

        Les informations sont extraites à partir des tags Vorbis Comment
        (TITLE, ARTIST, ALBUM, TRACKNUMBER, DATE/YEAR, GENRE) ainsi que
        de la durée du fichier.

        Returns:
            Metadata: Métadonnées extraites du fichier FLAC.
        """
        duration = None
        if self.audio and self.audio.info:
            duration = int(self.audio.info.length)

        title = self._get_vorbis("title")
        artist = self._get_vorbis("artist")
        album = self._get_vorbis("album")
        track_no = self._get_vorbis("tracknumber")
        year = self._get_vorbis("date") or self._get_vorbis("year")
        genre = self._get_vorbis("genre")

        return Metadata(
            title=title,
            artist=artist,
            album=album,
            track_no=track_no,
            duration_sec=duration,
            year=year,
            genre=genre,
        )

    def update_metadata(self,
                        title: Optional[str] = None,
                        artist: Optional[str] = None,
                        album: Optional[str] = None,
                        year: Optional[str] = None,
                        genre: Optional[str] = None,
                        track_no: Optional[str] = None) -> bool:
        """
        Met à jour les métadonnées Vorbis Comment du fichier FLAC.

        Pour chaque paramètre non None, le champ Vorbis correspondant
        est modifié.

        Args:
            title (str | None): Nouveau titre (champ ``TITLE``).
            artist (str | None): Nouvel artiste (champ ``ARTIST``).
            album (str | None): Nouvel album (champ ``ALBUM``).
            year (str | None): Nouvelle année (champ ``DATE``).
            genre (str | None): Nouveau genre (champ ``GENRE``).
            track_no (str | None): Nouveau n° de piste (champ ``TRACKNUMBER``).

        Returns:
            bool: True si la sauvegarde a réussi, False en cas d'erreur.
        """
        try:
            # Mettre à jour les champs fournis
            if title is not None:
                self.audio["TITLE"] = title
            if artist is not None:
                self.audio["ARTIST"] = artist
            if album is not None:
                self.audio["ALBUM"] = album
            if year is not None:
                self.audio["DATE"] = str(year)
            if genre is not None:
                self.audio["GENRE"] = genre
            if track_no is not None:
                self.audio["TRACKNUMBER"] = str(track_no)

            # Sauvegarder
            self.audio.save()
            return True
        except Exception as e:
            print(f"Erreur lors de la mise à jour des tags FLAC : {e}")
            return False

    def _format_date(self, date_str: str) -> str:
        """
        Formate une date en provenance de tags FLAC vers un format lisible.

        Cette méthode est similaire à :meth:`MP3AudioFile._format_date`
        et gère les formats :

        - ``YYYYMMDD`` ;
        - ``YYYY-MM-DD`` ;
        - ``YYYY``.

        Args:
            date_str (str): Date brute lue dans les tags.

        Returns:
            str: Date formatée ou chaîne brute si le format n'est pas
            reconnu.
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Format YYYYMMDD (ex: 20180705)
        if len(date_str) == 8 and date_str.isdigit():
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{day}/{month}/{year}"

        # Format YYYY-MM-DD (ex: 2018-07-05)
        elif "-" in date_str and len(date_str) == 10:
            parts = date_str.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"

        # Format YYYY seulement (ex: 2018)
        elif len(date_str) == 4 and date_str.isdigit():
            return date_str

        # Autre : retourner tel quel
        return date_str
