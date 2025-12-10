# -*- coding: utf-8 -*-
"""
directory_scanner.py

Exploration récursive d'un dossier pour trouver des fichiers audio MP3/FLAC.

Ce module propose une classe :class:`DirectoryScanner` qui permet de :

- parcourir récursivement une arborescence de dossiers ;
- filtrer les fichiers par extension (``.mp3``, ``.flac``) ;
- filtrer les fichiers par type MIME (``audio/mpeg``, ``audio/flac``, etc.) ;
- optionnellement, vérifier que le contenu audio est bien reconnu par
  la bibliothèque ``mutagen`` (sanity check).

Ce scanner est utilisé côté CLI et GUI pour construire la bibliothèque
musicale à partir d'un dossier racine choisi par l'utilisateur.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Set
import mimetypes
import os

# Vérification de contenu facultative via mutagen (écarte quelques faux positifs MIME)
from mutagen import File as MutagenFile


class DirectoryScanner:
    """
    Scanner de dossiers récursif pour fichiers audio.

    Le scanner applique plusieurs niveaux de filtrage :

    - **extension** : seuls les fichiers ``.mp3`` et ``.flac`` sont acceptés ;
    - **type MIME** : seuls les types audio attendus (``audio/mpeg``,
      ``audio/flac``, ``audio/mp3``, ``audio/x-flac``) sont conservés ;
    - **sanity check mutagen** (optionnel) : écarte les fichiers que
      :func:`mutagen.File` ne sait pas ouvrir comme audio.

    Il peut aussi ignorer les fichiers et dossiers cachés (ceux dont le nom
    commence par un point) selon la configuration.
    """

    #: Extensions supportées (en minuscules).
    SUPPORTED_EXTS: Set[str] = {".mp3", ".flac"}

    #: Types MIME supportés (selon les plateformes).
    SUPPORTED_MIMES: Set[str] = {
        "audio/mpeg",
        "audio/mp3",
        "audio/flac",
        "audio/x-flac",
    }

    def __init__(self, include_hidden: bool = False, sanity_check_with_mutagen: bool = True):
        """
        Initialise un scanner de répertoires.

        Args:
            include_hidden (bool): Si False, les fichiers et dossiers cachés
                (noms commençant par un point) sont ignorés.
            sanity_check_with_mutagen (bool): Si True, chaque fichier trouvé
                est également vérifié via :func:`mutagen.File` afin de s'assurer
                qu'il s'agit bien d'un fichier audio valide.
        """
        self.include_hidden = include_hidden
        self.sanity_check = sanity_check_with_mutagen

    def _is_hidden(self, path: Path) -> bool:
        """
        Indique si un chemin correspond à un fichier ou dossier "caché".

        Un fichier ou dossier est considéré comme caché s'il contient au
        moins un segment dont le nom commence par un point (``"."``).

        Args:
            path (Path): Chemin à tester.

        Returns:
            bool: True si le chemin est caché, False sinon.
        """
        return any(part.startswith(".") for part in path.parts)

    def _looks_supported(self, p: Path) -> bool:
        """
        Vérifie rapidement si un fichier a l'air d'être un fichier audio supporté.

        Le test se fait en deux temps :

        1. Vérification de l'extension (doit être dans :attr:`SUPPORTED_EXTS`) ;
        2. Vérification du type MIME déduit par :mod:`mimetypes` (doit être
           dans :attr:`SUPPORTED_MIMES`).

        Certains systèmes peuvent renvoyer ``None`` pour le type MIME des FLAC.
        Dans ce cas, si l'extension est ``.flac``, on tolère quand même.

        Args:
            p (Path): Chemin du fichier à tester.

        Returns:
            bool: True si le fichier semble supporté, False sinon.
        """
        if p.suffix.lower() not in self.SUPPORTED_EXTS:
            return False
        mime, _ = mimetypes.guess_type(str(p))
        if mime not in self.SUPPORTED_MIMES:
            # Certains systèmes renvoient None pour FLAC → on tolère si extension OK
            if p.suffix.lower() == ".flac" and mime is None:
                return True
            return False
        return True

    def _mutagen_ok(self, p: Path) -> bool:
        """
        Vérifie que ``mutagen`` reconnaît le fichier comme audio valide.

        Cette vérification permet de se protéger contre certains faux positifs
        du type MIME (par exemple un fichier renommé avec une extension .mp3
        mais qui n'est pas un vrai MP3).

        Args:
            p (Path): Chemin du fichier à tester.

        Returns:
            bool: True si mutagen reconnaît le fichier, False sinon.
        """
        try:
            mf = MutagenFile(str(p))
            return mf is not None
        except Exception:
            return False

    def iter_files(self, root: str | Path) -> Iterable[Path]:
        """
        Itère sur tous les fichiers audio valides dans l'arborescence.

        Cette méthode parcourt récursivement le dossier racine fourni et
        applique les différents filtres (fichiers cachés, extension, type
        MIME, sanity check mutagen). Seuls les fichiers considérés comme
        valides sont renvoyés.

        Args:
            root (str | Path): Dossier racine à partir duquel effectuer
                la recherche.

        Yields:
            Path: Chemins absolus des fichiers audio valides trouvés.
        """
        root_path = Path(root)
        if not root_path.exists():
            # Si la racine n'existe pas, le générateur ne produit rien.
            return

        for dirpath, dirnames, filenames in os.walk(str(root_path)):
            # Option : filtrer les dossiers cachés
            if not self.include_hidden:
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]

            for name in filenames:
                p = Path(dirpath, name)

                if not self.include_hidden and self._is_hidden(p):
                    continue

                if not self._looks_supported(p):
                    continue

                if self.sanity_check and not self._mutagen_ok(p):
                    # MIME disait OK mais mutagen ne sait pas l'ouvrir → on écarte
                    continue

                yield p.resolve()

    def scan(self, root: str | Path) -> List[str]:
        """
        Retourne la liste des chemins de fichiers audio valides sous forme de chaînes.

        Cette méthode est un simple utilitaire au-dessus de :meth:`iter_files`
        pour les usages où l'on préfère manipuler directement des ``str``
        (par exemple en CLI).

        Args:
            root (str | Path): Dossier racine à scanner.

        Returns:
            list[str]: Liste des chemins absolus des fichiers audio trouvés.
        """
        return [str(p) for p in self.iter_files(root)]
