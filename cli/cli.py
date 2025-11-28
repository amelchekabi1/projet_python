import argparse
import sys
import os

# Ajout du chemin pour importer library
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library.xspf_writer import write_xspf
from library.audiofile import AudioFile
from library.directory_scanner import DirectoryScanner


def parse_arguments():
    """
    Parse les arguments de la ligne de commande.
    
    Returns:
        argparse.Namespace: Arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="Gestionnaire de bibliothèque musicale MP3/FLAC",
        epilog="Exemples:\n"
               "  python3 cli.py -f musique.mp3\n"
               "  python3 cli.py -d ./music/ -o playlist.xspf\n"
               "  python3 cli.py -p musique.mp3",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Groupe mutuellement exclusif : soit fichier, soit dossier, soit play
    group = parser.add_mutually_exclusive_group(required=False)
    
    group.add_argument(
        '-f', '--file',
        type=str,
        metavar='FICHIER',
        help='Analyser un fichier MP3 ou FLAC'
    )
    
    group.add_argument(
        '-d', '--directory',
        type=str,
        metavar='DOSSIER',
        help='Scanner un dossier récursivement'
    )
    
    group.add_argument(
        '-p', '--play',
        type=str,
        metavar='FICHIER',
        help='Jouer un fichier audio'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        metavar='FICHIER.xspf',
        help='Fichier de sortie pour la playlist (nécessite -d)'
    )
    
    return parser.parse_args()


def validate_audio_file(file_path):
    """
    Valide qu'un fichier existe et est au bon format.
    
    Args:
        file_path (str): Chemin vers le fichier
        
    Raises:
        SystemExit: Si le fichier n'est pas valide
    """
    if not os.path.exists(file_path):
        print(f" Erreur : Le fichier '{file_path}' n'existe pas.")
        sys.exit(1)
    
    # Vérifier l'extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.mp3', '.flac']:
        print(f" Erreur : Format non supporté '{ext}'. Seulement MP3 et FLAC.")
        sys.exit(1)


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
        # Utiliser la factory method from_path
        audio = AudioFile.from_path(file_path)
        
        # Récupérer les métadonnées
        metadata = audio.read_metadata()
        metadata_dict = metadata.to_dict()
        
        # Informations du fichier
        print(" Informations du fichier :")
        print(f"  - Nom      : {os.path.basename(file_path)}")
        print(f"  - Chemin   : {os.path.abspath(file_path)}")
        print(f"  - Taille   : {os.path.getsize(file_path):,} octets")
        
        # Déterminer le format
        ext = os.path.splitext(file_path)[1].lower()
        print(f"  - Format   : {ext[1:].upper()}")
        
        # Métadonnées audio
        print("\n🎵 Métadonnées :")
        print(f"  - Titre       : {metadata_dict['title'] or 'Inconnu'}")
        print(f"  - Artiste     : {metadata_dict['artist'] or 'Inconnu'}")
        print(f"  - Album       : {metadata_dict['album'] or 'Inconnu'}")
        print(f"  - Piste n°    : {metadata_dict['track_no'] or 'Inconnu'}")
        print(f"  - Année       : {metadata_dict['year'] or 'Inconnu'}")
        print(f"  - Genre       : {metadata_dict['genre'] or 'Inconnu'}")
        
        duration = metadata_dict['duration_sec']
        if duration:
            minutes = duration // 60
            seconds = duration % 60
            print(f"  - Durée       : {duration} secondes ({minutes}:{seconds:02d})")
        else:
            print(f"  - Durée       : Inconnue")
        
    except ValueError as e:
        print(f" Erreur : {e}")
        sys.exit(1)
    except Exception as e:
        print(f" Erreur lors de la lecture des métadonnées : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def scan_directory(directory_path, output_file=None):
    """
    Scanne un dossier récursivement et liste les fichiers audio.
    Génère optionnellement une playlist XSPF.
    
    Args:
        directory_path (str): Chemin vers le dossier
        output_file (str, optional): Fichier de sortie pour la playlist
    """
    print(f"\n{'='*60}")
    print(f"Scan du dossier : {directory_path}")
    print(f"{'='*60}\n")
    
    # Vérifier que le dossier existe
    if not os.path.isdir(directory_path):
        print(f" Erreur : Le dossier '{directory_path}' n'existe pas.")
        sys.exit(1)
    
    print("🔍 Recherche de fichiers MP3 et FLAC...\n")
    
    # Utiliser DirectoryScanner
    scanner = DirectoryScanner(include_hidden=False, sanity_check_with_mutagen=True)
    
    try:
        found_files = scanner.scan(directory_path)
        
        # Afficher les fichiers trouvés
        for file_path in found_files:
            rel_path = os.path.relpath(file_path, directory_path)
            print(f"  ✓ {rel_path}")
        
        print(f"\n Résultat : {len(found_files)} fichier(s) audio valide(s)")
        
        # Génération de la playlist si demandée
        if output_file and found_files:
            generate_playlist(found_files, output_file)
        elif output_file and not found_files:
            print("\n  Aucun fichier trouvé, playlist non créée.")
            
    except Exception as e:
        print(f" Erreur lors du scan : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def generate_playlist(files, output_file):
    """
    Génère une playlist XSPF à partir d'une liste de fichiers.
    
    Args:
        files (list): Liste des chemins de fichiers audio
        output_file (str): Chemin du fichier XSPF de sortie
    """
    print(f"\n Génération de la playlist : {output_file}")
    
    try:
        from library.playlist import create_playlist_from_files
        from library.xspf_writer import write_xspf
        
        # Créer la playlist avec extraction automatique des métadonnées
        playlist = create_playlist_from_files(files, "Playlist générée automatiquement")
        
        # Écrire le fichier XSPF
        write_xspf(playlist, output_file)
        
        print(f" Playlist créée avec succès : {len(playlist.tracks)} piste(s)")
        print(f" Validez votre playlist sur : https://validator.xspf.org/")
        
    except Exception as e:
        print(f" Erreur lors de la génération de la playlist : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def play_file(file_path):
    """
    Joue un fichier audio.
    
    Args:
        file_path (str): Chemin vers le fichier
    """
    print(f"\n{'='*60}")
    print(f"Lecture du fichier : {file_path}")
    print(f"{'='*60}\n")
    
    validate_audio_file(file_path)
    
    try:
        # Afficher les métadonnées d'abord
        audio = AudioFile.from_path(file_path)
        metadata = audio.read_metadata()
        
        print(" Lecture en cours :")
        print(f"  - Titre   : {metadata.title or 'Inconnu'}")
        print(f"  - Artiste : {metadata.artist or 'Inconnu'}")
        print(f"  - Album   : {metadata.album or 'Inconnu'}")
        
        if metadata.duration_sec:
            minutes = metadata.duration_sec // 60
            seconds = metadata.duration_sec % 60
            print(f"  - Durée   : {minutes}:{seconds:02d}")
        
        print("\n⏯  Appuyez sur Ctrl+C pour arrêter...\n")
        
        # Initialiser pygame mixer
        import pygame
        pygame.mixer.init()
        
        # Charger et jouer le fichier
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        # Attendre que la lecture se termine
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        print("\n✅ Lecture terminée.")
        
    except ImportError:
        print("Erreur : pygame n'est pas installé.")
        print("Installez-le avec : pip install pygame")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏸ Lecture interrompue.")
        pygame.mixer.music.stop()
    except Exception as e:
        print(f" Erreur lors de la lecture : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Fonction principale du programme CLI."""
    
    # Si aucun argument, afficher l'aide
    if len(sys.argv) == 1:
        print(" Erreur : Aucun argument fourni.")
        print(" Utilisez -h ou --help pour afficher l'aide.\n")
        sys.exit(1)
    
    # Parser les arguments
    args = parse_arguments()
    
    # Vérifier que -o est utilisé avec -d uniquement
    if args.output and not args.directory:
        print(" Erreur : L'option -o (output) nécessite l'option -d (directory)")
        print(" Exemple : python3 cli.py -d ./music/ -o playlist.xspf\n")
        sys.exit(1)
    
    # Traitement selon les options
    if args.file:
        display_file_metadata(args.file)
    
    elif args.directory:
        scan_directory(args.directory, args.output)
    
    elif args.play:
        play_file(args.play)
    
    else:
        print(" Erreur : Option non reconnue.")
        print(" Utilisez -h ou --help pour afficher l'aide.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Programme interrompu par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"\n Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)