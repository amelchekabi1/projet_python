# -*- coding: utf-8 -*-
"""
validation.py

Fonctions de validation simples pour les fichiers audio.
Ce module vérifie l’existence du fichier et son extension,
conformément aux exigences du projet :

- Seuls les fichiers MP3 et FLAC sont considérés comme valides.
- Toute erreur de validation déclenche une exception explicite.

Module utilisé par la CLI et parfois par le scanner de fichiers.
"""

import os


def validate_audio_file(file_path: str) -> bool:
    """
    Vérifie qu'un fichier audio est valide pour le traitement.

    Cette fonction effectue trois vérifications successives :

    1. **Présence sur le disque** : le chemin doit pointer vers un fichier existant.
    2. **Nature du chemin** : le chemin doit correspondre à un fichier
