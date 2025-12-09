import argparse
import sys
import os
from library.audiofile import AudioFile
from library.validation import validate_audio_file
import pygame


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library.xspf_writer import write_xspf

def format_duration(seconds):
    """
    Formate une durée en secondes vers 'X min Y s'.
    
    Args:
        seconds (int): Durée en secondes
        
    Returns:
        str: Durée formatée
    """
    if not seconds:
        return "Inconnue"
    
    minutes = seconds // 60
    secs = seconds % 60
    
    if minutes > 0:
        return f"{minutes} min {secs} s"
    else:
        return f"{secs} s"

# -----------------------------------------------------
#  VALIDATION DU FICHIER AUDIO
# -----------------------------------------------------
def validate_audio_file(file_path):
    """Vérifie que le fichier existe et a une extension valide."""
    if not os.path.exists(file_path):
        raise ValueError(f"Le fichier '{file_path}' n'existe pas.")
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.mp3', '.flac']:
        raise ValueError("Format non supporté. Seulement MP3 et FLAC.")


# -----------------------------------------------------
#  PARSING DES ARGUMENTS
# -----------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Gestionnaire de bibliothèque musicale MP3/FLAC",
        epilog="Exemples:\n"
               "  python3 cli.py -f musique.mp3\n"
               "  python3 cli.py -e musique.mp3\n"
               "  python3 cli.py -d ./music/ -o playlist.xspf\n"
               "  python3 cli.py -p musique.mp3",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument('-f', '--file', type=str, help='Analyser un fichier MP3 ou FLAC')
    group.add_argument('-d', '--directory', type=str, help='Scanner un dossier récursivement')
    group.add_argument('-p', '--play', type=str, help='Jouer un fichier audio')
    group.add_argument('-e', '--edit', type=str, help="Éditer les métadonnées d'un fichier")

    parser.add_argument('-o', '--output', type=str, metavar='FICHIER.xspf',
                        help='Fichier de sortie pour la playlist (format XSPF)')

    return parser.parse_args()


# -----------------------------------------------------
#  ÉDITION DES MÉTADONNÉES
# -----------------------------------------------------
def edit_file_metadata(file_path):
    print(f"\n{'='*60}")
    print(f"Édition des métadonnées : {file_path}")
    print(f"{'='*60}\n")

    validate_audio_file(file_path)

    try:
        audio = AudioFile.from_path(file_path)
        metadata = audio.read_metadata()

        print(" Métadonnées actuelles :")
        print(f"  - Titre    : {metadata.title or '(vide)'}")
        print(f"  - Artiste  : {metadata.artist or '(vide)'}")
        print(f"  - Album    : {metadata.album or '(vide)'}")
        print(f"  - Année    : {metadata.year or '(vide)'}")
        print(f"  - Genre    : {metadata.genre or '(vide)'}")
        print(f"  - Piste n° : {metadata.track_no or '(vide)'}")
        print(f"  - Durée    : {format_duration(metadata.duration_sec)}")
        print("\n" + "="*60)
        print("  ÉDITION - Entrée = conserver valeur actuelle")
        print("="*60 + "\n")

        new_title = input(f"Nouveau titre [{metadata.title or ''}] : ").strip()
        new_artist = input(f"Nouvel artiste [{metadata.artist or ''}] : ").strip()
        new_album = input(f"Nouvel album [{metadata.album or ''}] : ").strip()
        new_year = input(f"Nouvelle année [{metadata.year or ''}] : ").strip()
        new_genre = input(f"Nouveau genre [{metadata.genre or ''}] : ").strip()
        new_track = input(f"Nouveau n° de piste [{metadata.track_no or ''}] : ").strip()

        print("\n" + "="*60)
        print(" Résumé des modifications :")
        print("="*60)

        changes = []

        if new_title and new_title != metadata.title:
            print(f"  Titre    : {metadata.title or '(vide)'} → {new_title}")
            changes.append(('title', new_title))
        if new_artist and new_artist != metadata.artist:
            print(f"  Artiste  : {metadata.artist or '(vide)'} → {new_artist}")
            changes.append(('artist', new_artist))
        if new_album and new_album != metadata.album:
            print(f"  Album    : {metadata.album or '(vide)'} → {new_album}")
            changes.append(('album', new_album))
        if new_year and new_year != metadata.year:
            print(f"  Année    : {metadata.year or '(vide)'} → {new_year}")
            changes.append(('year', new_year))
        if new_genre and new_genre != metadata.genre:
            print(f"  Genre    : {metadata.genre or '(vide)'} → {new_genre}")
            changes.append(('genre', new_genre))
        if new_track and new_track != metadata.track_no:
            print(f"  Piste n° : {metadata.track_no or '(vide)'} → {new_track}")
            changes.append(('track_no', new_track))

        if not changes:
            print("\n  Aucune modification.")
            return

        print("\n" + "="*60)
        confirm = input("Confirmer les modifications ? (o/N) : ").strip().lower()

        if confirm not in ['o', 'oui', 'y', 'yes']:
            print("\n Modifications annulées.")
            return

        success = audio.update_metadata(
            title=new_title or None,
            artist=new_artist or None,
            album=new_album or None,
            year=new_year or None,
            genre=new_genre or None,
            track_no=new_track or None
        )

        if success:
            print("\n Métadonnées mises à jour !")
        else:
            print("\n Erreur lors de la sauvegarde.")
            sys.exit(1)

    except Exception as e:
        print(f" Erreur : {e}")
        sys.exit(1)


# -----------------------------------------------------
#  AFFICHAGE DES MÉTADONNÉES
# -----------------------------------------------------
def display_file_metadata(file_path):
    """
    Affiche les métadonnées d'un fichier audio.
    
    Args:
        file_path (str): Chemin vers le fichier
    """
    print(f"\n{'='*60}")
    print(f"Analyse du fichier : {file_path}")
    print(f"{'='*60}\n")

    validate_audio_file(file_path)

    try:
        # Utiliser la classe AudioFile pour lire les métadonnées
        audio = AudioFile.from_path(file_path)
        metadata = audio.read_metadata()
        metadata_dict = metadata.to_dict()
        
        # Informations du fichier
        print(" Informations du fichier :")
        print(f"  - Nom      : {os.path.basename(file_path)}")
        print(f"  - Chemin   : {os.path.abspath(file_path)}")
        print(f"  - Taille   : {os.path.getsize(file_path):,} octets")
        print(f"  - Format   : {os.path.splitext(file_path)[1][1:].upper()}")
        
        # Métadonnées audio
        print("\n Métadonnées :")
        print(f"  - Titre       : {metadata_dict['title'] or 'Inconnu'}")
        print(f"  - Artiste     : {metadata_dict['artist'] or 'Inconnu'}")
        print(f"  - Album       : {metadata_dict['album'] or 'Inconnu'}")
        print(f"  - Piste n°    : {metadata_dict['track_no'] or 'Inconnu'}")
        print(f"  - Année       : {metadata_dict['year'] or 'Inconnue'}")
        print(f"  - Genre       : {metadata_dict['genre'] or 'Inconnu'}")
        print(f"  - Durée       : {format_duration(metadata_dict['duration_sec'])}")
        
    except ValueError as e:
        print(f" Erreur : {e}")
        sys.exit(1)
    except Exception as e:
        print(f" Erreur lors de la lecture des métadonnées : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# -----------------------------------------------------
#  SCAN DE DOSSIER + PLAYLIST XSPF
# -----------------------------------------------------
def scan_directory(directory_path, output_file=None):
    print(f"\n{'='*60}")
    print(f"Scan du dossier : {directory_path}")
    print(f"{'='*60}\n")

    if not os.path.isdir(directory_path):
        print(f" Erreur : Le dossier '{directory_path}' n'existe pas.")
        sys.exit(1)

    print("🔍 Recherche de fichiers MP3 et FLAC...\n")

    found_files = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith(('.mp3', '.flac')):
                fp = os.path.join(root, file)
                found_files.append(fp)
                print(f"  ✓ {fp}")

    print(f"\n Total : {len(found_files)} fichier(s) trouvé(s)")

    if output_file:
        print(f"\n Génération de la playlist : {output_file}")

        class SimpleTrack:
            def __init__(self, path):
                self.path = os.path.abspath(path)
                self.title = os.path.basename(path)
                self.artist = "Artiste inconnu"
                self.album = "Album inconnu"
                self.duration = None

        class SimplePlaylist:
            def __init__(self, name, files):
                self.name = name
                self.tracks = [SimpleTrack(f) for f in files]

        playlist = SimplePlaylist("Playlist générée automatiquement", found_files)
        write_xspf(playlist, output_file)

        print("\n Playlist générée avec succès !")


# -----------------------------------------------------
#  LECTURE AUDIO
# -----------------------------------------------------
def play_file(file_path):
    print(f"\n{'='*60}")
    print(f"Lecture du fichier : {file_path}")
    print(f"{'='*60}\n")

    if not os.path.exists(file_path):
        print(f" Le fichier '{file_path}' n'existe pas.")
        sys.exit(1)

    print("🎵 Lecture en cours...")
    play_audio(file_path)


def play_audio(path):
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        print(" Lecture en cours... (CTRL+C pour arrêter)")

        # Boucle qui attend la fin de la lecture
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f" Impossible de lire le fichier : {e}")


# -----------------------------------------------------
#  MAIN
# -----------------------------------------------------
def main():
    if len(sys.argv) == 1:
        print(" Aucun argument fourni.")
        print(" Utilisez -h ou --help pour l'aide.\n")
        sys.exit(1)

    args = parse_arguments()

    if args.file:
        display_file_metadata(args.file)
    elif args.directory:
        scan_directory(args.directory, args.output)
    elif args.play:
        play_file(args.play)
    elif args.edit:
        edit_file_metadata(args.edit)
    else:
        print(" Option non reconnue.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Programme interrompu par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"\n Erreur inattendue : {e}")
        sys.exit(1)
