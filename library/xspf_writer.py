# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
from pathlib import Path

def write_xspf(playlist, output_file):
    """Génère un fichier XSPF."""
    root = ET.Element("playlist", version="1", xmlns="http://xspf.org/ns/0/")
    
    # Titre
    title_elem = ET.SubElement(root, "title")
    title_elem.text = getattr(playlist, 'title', getattr(playlist, 'name', 'Sans titre'))
    
    # Liste
    tracklist = ET.SubElement(root, "trackList")
    
    for track in playlist.tracks:
        track_elem = ET.SubElement(tracklist, "track")
        
        # Location
        loc = ET.SubElement(track_elem, "location")
        if hasattr(track, 'location'):
            loc.text = track.location
        else:
            loc.text = f"file://{getattr(track, 'path', '')}"
        
        # Titre
        if hasattr(track, 'title') and track.title:
            ET.SubElement(track_elem, "title").text = str(track.title)
        
        # Creator (support creator OU artist)
        creator = getattr(track, 'creator', getattr(track, 'artist', None))
        if creator:
            ET.SubElement(track_elem, "creator").text = str(creator)
        
        # Album
        if hasattr(track, 'album') and track.album:
            ET.SubElement(track_elem, "album").text = str(track.album)
        
        # Duration
        if hasattr(track, 'duration') and track.duration:
            ET.SubElement(track_elem, "duration").text = str(int(track.duration))
    
    # Sauvegarder
    _indent(root)
    tree = ET.ElementTree(root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f" Playlist sauvegardée : {output_file} ({len(playlist.tracks)} piste(s))")

def _indent(elem, level=0):
    """Indentation."""
    i = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i