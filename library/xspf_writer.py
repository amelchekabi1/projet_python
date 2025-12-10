# -*- coding: utf-8 -*-
"""
xspf_writer.py

Génération de fichiers XSPF (XML Shareable Playlist Format) à partir
d’objets Playlist / Track utilisés dans le projet.

Le module produit un fichier XSPF lisible par VLC, Foobar2000, Clementine,
et par la CLI/GUI du projet. 

Principales caractéristiques :
- Inclus le titre de la playlist
- Écrit chaque piste avec : location, title, creator, album, duration
- Compatible Linux, Windows et WSL
"""

import xml.etree.ElementTree as ET
from pathlib import Path


def write_xspf(playlist, output_file: str) -> None:
    """
    Génère un fichier XSPF basé sur les pistes d'une playlist.

    Cette fonction sérialise les objets `Track` en XML selon la norme XSPF :
    https://xspf.org

    Chaque piste écrite inclut, si disponible :
        - location  (URI du fichier local)
        - title     (titre du morceau)
        - creator   (artiste)
        - album     (album)
        - duration  (durée en millisecondes ou secondes, compatible VLC)

    Args:
        playlist: Objet possédant un attribut `tracks` (liste de Track)
                  et `title` ou `name` pour nommer la playlist.
        output_file (str): Chemin du fichier XSPF à créer.

    Returns:
        None – écrit un fichier sur disque et affiche un message de confirmation.

    Exemple :
        >>> write_xspf(my_playlist, "playlist.xspf")
    """
    root = ET.Element("playlist", version="1", xmlns="http://xspf.org/ns/0/")

    # Donne un titre à la playlist
    title_elem = ET.SubElement(root, "title")
    title_elem.text = getattr(playlist, "title",
                      getattr(playlist, "name", "Sans titre"))

    # Conteneur des pistes
    tracklist = ET.SubElement(root, "trackList")

    # Écriture de toutes les pistes
    for track in playlist.tracks:
        track_elem = ET.SubElement(tracklist, "track")

        # LOCATION (URI)
        loc = ET.SubElement(track_elem, "location")

        if hasattr(track, "location"):
            loc.text = track.location
        else:
            # fallback minimal
            path = getattr(track, "path", "")
            loc.text = f"file://{path}"

        # TITLE
        if getattr(track, "title", None):
            ET.SubElement(track_elem, "title").text = str(track.title)

        # CREATOR (Artiste)
        creator = getattr(track, "creator", getattr(track, "artist", None))
        if creator:
            ET.SubElement(track_elem, "creator").text = str(creator)

        # ALBUM
        if getattr(track, "album", None):
            ET.SubElement(track_elem, "album").text = str(track.album)

        # DURATION
        if getattr(track, "duration", None):
            # convertit éventuellement en entier
            ET.SubElement(track_elem, "duration").text = str(int(track.duration))

    # Mise en forme lisible (indentation)
    _indent(root)

    # Sauvegarde dans un fichier XSPF
    tree = ET.ElementTree(root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)

    print(f" Playlist sauvegardée : {output_file} ({len(playlist.tracks)} piste(s))")


def _indent(elem, level: int = 0) -> None:
    """
    Applique une indentation lisible à un arbre XML.
    Utile pour obtenir un XSPF bien formaté.

    Args:
        elem: Élément XML racine ou enfant.
        level (int): Niveau d'indentation.

    Returns:
        None – modifie l'arbre XML en place.
    """
    i = "\n" + "  " * level

    if len(elem):
        # Élément avec enfants → indent
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "

        if not elem.tail or not elem.tail.strip():
            elem.tail = i

        for child in elem:
            _indent(child, level + 1)

        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        # Élément sans enfants → juste tail
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
