import os

def validate_audio_file(file_path):
    """
    Vérifie que le fichier existe et que son extension est valide (MP3/FLAC).
    Renvoie True si ok, sinon lève une exception.
    """

    if not os.path.exists(file_path):
        raise ValueError(f"Le fichier '{file_path}' n'existe pas.")

    if not os.path.isfile(file_path):
        raise ValueError(f"'{file_path}' n'est pas un fichier valide.")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.mp3', '.flac']:
        raise ValueError("Format non supporté. Seulement MP3 et FLAC.")

    return True
