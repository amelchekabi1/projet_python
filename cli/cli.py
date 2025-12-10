"""
Module principal de la ligne de commande (CLI) du projet de gestion de
bibliothèque musicale.

Ce module permet, via des options en ligne de commande, de :

- analyser un fichier audio (MP3/FLAC) et afficher ses métadonnées ;
- scanner un dossier récursivement pour trouver les fichiers audio ;
- générer une playlist XSPF à partir d'un dossier ;
- lire un fichier audio (avec commandes interactives dans le terminal) ;
- lire une playlist XSPF (avec suivant/précédent/stop) ;
- éditer et sauvegarder les métadonnées (TAGS) d'un fichier ;
- interroger l'API MusicBrainz pour enrichir les informations d'un morceau.

Il s'appuie sur les modules du package ``library`` (audiofile, directory_scanner,
playlist, xspf_writer, etc.).
"""

import argparse
import sys
import os
from library.audiofile import AudioFile
from library.validation import validate_audio_file
from library.directory_scanner import DirectoryScanner
from library.playlist import load_playlist_from_xspf

# Ajout du dossier parent dans le chemin d'import pour permettre
# l'import du module xspf_writer lorsque le script est exécuté directement.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library.xspf_writer import write_xspf


def format_duration(seconds):
    """
    Formate une durée en secondes vers une chaîne lisible.

    Exemple de format : ``"3 min 25 s"`` ou ``"42 s"``.

    Args:
        seconds (int | None): Durée en secondes. Peut être None si la durée
            n'est pas connue.

    Returns:
        str: Une chaîne représentant la durée, ou ``"Inconnue"`` si la
        durée n'est pas fournie.
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
    """
    Vérifie que le fichier existe et possède une extension audio supportée.

    Cette fonction complète une première vérification simple (existence,
    extension). Les vérifications plus poussées (MIME, mutagen) sont réalisées
    dans d'autres modules lors du scan de répertoires.

    Args:
        file_path (str): Chemin vers le fichier audio à valider.

    Raises:
        ValueError: Si le fichier n'existe pas ou si l'extension n'est pas
            supportée (seulement ``.mp3`` et ``.flac``).
    """
    if not os.path.exists(file_path):
        raise ValueError(f"Le fichier '{file_path}' n'existe pas.")
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.mp3', '.flac']:
        raise ValueError("Format non supporté. Seulement MP3 et FLAC.")


# -----------------------------------------------------
#  PARSING DES ARGUMENTS
# -----------------------------------------------------
def parse_arguments():
    """
    Construit et analyse la ligne de commande de l'application.

    Les options principales sont mutuellement exclusives :

    - ``-f / --file`` : analyser un fichier audio ;
    - ``-d / --directory`` : scanner un dossier ;
    - ``-p / --play`` : jouer un fichier ;
    - ``-e / --edit`` : éditer les métadonnées d'un fichier ;
    - ``--api-info`` : interroger l'API MusicBrainz pour un fichier.

    Options additionnelles :

    - ``-o / --output`` : générer un fichier XSPF lors du scan ;
    - ``-P / --play-list`` : lire une playlist XSPF existante.

    Returns:
        argparse.Namespace: Objet contenant les options et arguments
        fournis par l'utilisateur.
    """
    parser = argparse.ArgumentParser(
        description="Gestionnaire de bibliothèque musicale MP3/FLAC",
        epilog=(
            "Exemples:\n"
            "  python3 cli.py -f musique.mp3\n"
            "  python3 cli.py -e musique.mp3\n"
            "  python3 cli.py -d ./music/ -o playlist.xspf\n"
            "  python3 cli.py -p musique.mp3\n"
            "  python3 cli.py -P playlist.xspf"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument(
        '-f', '--file',
        type=str,
        help='Analyser un fichier MP3 ou FLAC'
    )
    group.add_argument(
        '-d', '--directory',
        type=str,
        help='Scanner un dossier récursivement'
    )
    group.add_argument(
        '-p', '--play',
        type=str,
        help='Jouer un fichier audio'
    )
    group.add_argument(
        '-e', '--edit',
        type=str,
        help="Éditer les métadonnées d'un fichier"
    )
    group.add_argument(
        '--api-info',
        dest='api_info',
        type=str,
        help="Rechercher des informations en ligne (MusicBrainz) pour un fichier audio"
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        metavar='FICHIER.xspf',
        help='Fichier de sortie pour la playlist (format XSPF)'
    )
    parser.add_argument(
        "-P", "--play-list",
        dest="playlist",
        help="Lire une playlist XSPF existante"
    )

    return parser.parse_args()


# -----------------------------------------------------
#  ÉDITION DES MÉTADONNÉES
# -----------------------------------------------------
def edit_file_metadata(file_path):
    """
    Lance un assistant interactif pour éditer les métadonnées d'un fichier.

    Le fichier est d'abord analysé afin d'afficher les métadonnées actuelles.
    L'utilisateur peut ensuite saisir de nouvelles valeurs (ou laisser vide
    pour conserver les anciennes). Une confirmation est demandée avant la
    sauvegarde.

    Args:
        file_path (str): Chemin du fichier audio dont on veut modifier
            les métadonnées.

    Raises:
        SystemExit: En cas d'erreur critique lors de la modification,
            le programme se termine avec un code de sortie non nul.
    """
    print(f"\n{'=' * 60}")
    print(f"Édition des métadonnées : {file_path}")
    print(f"{'=' * 60}\n")

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
        print("\n" + "=" * 60)
        print("  ÉDITION - Entrée = conserver valeur actuelle")
        print("=" * 60 + "\n")

        new_title = input(f"Nouveau titre [{metadata.title or ''}] : ").strip()
        new_artist = input(f"Nouvel artiste [{metadata.artist or ''}] : ").strip()
        new_album = input(f"Nouvel album [{metadata.album or ''}] : ").strip()
        new_year = input(f"Nouvelle année [{metadata.year or ''}] : ").strip()
        new_genre = input(f"Nouveau genre [{metadata.genre or ''}] : ").strip()
        new_track = input(f"Nouveau n° de piste [{metadata.track_no or ''}] : ").strip()

        print("\n" + "=" * 60)
        print(" Résumé des modifications :")
        print("=" * 60)

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

        print("\n" + "=" * 60)
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
    Affiche les informations principales et les métadonnées d'un fichier audio.

    Le fichier est vérifié puis analysé via la classe :class:`AudioFile`.
    Les informations de base (nom, chemin, taille, format) ainsi que les
    métadonnées (titre, artiste, album, etc.) sont affichées dans la console.

    Args:
        file_path (str): Chemin du fichier audio à analyser.

    Raises:
        SystemExit: En cas d'erreur de validation ou de lecture des
            métadonnées, le programme se termine avec un code de sortie
            non nul.
    """
    print(f"\n{'=' * 60}")
    print(f"Analyse du fichier : {file_path}")
    print(f"{'=' * 60}\n")

    validate_audio_file(file_path)

    try:
        audio = AudioFile.from_path(file_path)
        metadata = audio.read_metadata()
        metadata_dict = metadata.to_dict()

        print(" Informations du fichier :")
        print(f"  - Nom      : {os.path.basename(file_path)}")
        print(f"  - Chemin   : {os.path.abspath(file_path)}")
        print(f"  - Taille   : {os.path.getsize(file_path):,} octets")
        print(f"  - Format   : {os.path.splitext(file_path)[1][1:].upper()}")

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
    """
    Scanne récursivement un dossier à la recherche de fichiers audio valides.

    Les fichiers trouvés (MP3/FLAC valides selon ``DirectoryScanner``) sont
    listés dans la console. Si un fichier XSPF de sortie est fourni, une
    playlist est générée à partir des fichiers trouvés.

    Args:
        directory_path (str): Chemin du dossier à scanner.
        output_file (str | None): Chemin du fichier XSPF de sortie à générer.
            Si None, aucune playlist n'est créée.

    Raises:
        SystemExit: Si le dossier n'existe pas.
    """
    print(f"\n{'=' * 60}")
    print(f"Scan du dossier : {directory_path}")
    print(f"{'=' * 60}\n")

    if not os.path.isdir(directory_path):
        print(f" Erreur : Le dossier '{directory_path}' n'existe pas.")
        sys.exit(1)

    print("🔍 Recherche de fichiers MP3 et FLAC...\n")

    scanner = DirectoryScanner(sanity_check_with_mutagen=True)
    found_files = scanner.scan(directory_path)

    if not found_files:
        print(" Aucun fichier audio valide trouvé.")
    else:
        for fp in found_files:
            print(f"  ✓ {fp}")

    print(f"\n Total : {len(found_files)} fichier(s) trouvé(s)")

    if output_file:
        print(f"\n Génération de la playlist : {output_file}")

        class SimpleTrack:
            """
            Objet léger représentant une piste pour la génération XSPF.

            Cette classe ne couvre que les champs nécessaires à
            :func:`write_xspf`.
            """

            def __init__(self, path):
                """
                Initialise une piste simplifiée à partir d'un chemin de fichier.

                Les métadonnées sont lues lorsque cela est possible. En cas
                d'échec, des valeurs par défaut sont utilisées.

                Args:
                    path (str): Chemin du fichier audio.
                """
                self.path = os.path.abspath(path)
                try:
                    audio = AudioFile.from_path(path)
                    md = audio.read_metadata()
                    self.title = md.title or os.path.basename(path)
                    self.artist = md.artist or "Artiste inconnu"
                    self.album = md.album or "Album inconnu"
                    self.duration = md.duration_sec
                except Exception:
                    self.title = os.path.basename(path)
                    self.artist = "Artiste inconnu"
                    self.album = "Album inconnu"
                    self.duration = None

        class SimplePlaylist:
            """
            Représente une playlist minimale pour la génération XSPF.
            """

            def __init__(self, name, files):
                """
                Construit une playlist à partir d'une liste de fichiers.

                Args:
                    name (str): Nom de la playlist.
                    files (list[str]): Liste des chemins de fichiers audio.
                """
                self.name = name
                self.tracks = [SimpleTrack(f) for f in files]

        playlist = SimplePlaylist("Playlist générée automatiquement", found_files)
        write_xspf(playlist, output_file)

        print("\n Playlist générée avec succès !")


# -----------------------------------------------------
#  LECTURE AUDIO (INTERACTIF)
# -----------------------------------------------------
def play_audio_interactive(path, allow_next_prev=False):
    """
    Joue un fichier audio dans le terminal avec des contrôles clavier.

    Commandes disponibles :

    - ``a`` : pause ;
    - ``r`` : reprise ;
    - ``s`` : stop ;
    - ``n`` : piste suivante (si ``allow_next_prev=True``) ;
    - ``p`` : piste précédente (si ``allow_next_prev=True``).

    Le comportement de navigation (next/prev) est utilisé par la lecture
    de playlist.

    Args:
        path (str): Chemin du fichier audio à jouer.
        allow_next_prev (bool): Si True, autorise les commandes ``n`` et ``p``
            pour gérer la navigation dans une playlist.

    Returns:
        str: Une des valeurs suivantes selon l'action de l'utilisateur ou
        l'état de lecture :

        - ``"next"`` : passer à la piste suivante ;
        - ``"prev"`` : revenir à la piste précédente ;
        - ``"stop"`` : arrêter la lecture ;
        - ``"end"`` : la piste s'est terminée naturellement.
    """
    import pygame

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        print(f"\n🎵 Lecture : {path}")
        if allow_next_prev:
            print("Commandes : [a = pause] [r = reprise] [n = suivant] [p = précédent] [s = stop]")
        else:
            print("Commandes : [a = pause] [r = reprise] [s = stop]")
        print("(CTRL+C pour forcer l'arrêt)\n")

        paused = False

        while True:
            if not paused and not pygame.mixer.music.get_busy():
                print("🎶 Piste terminée.")
                return "end"

            cmd = input("> ").strip().lower()

            if cmd == "a":
                if not paused:
                    pygame.mixer.music.pause()
                    paused = True
                    print("⏸️  Lecture en pause.")
                else:
                    print("La lecture est déjà en pause.")
            elif cmd == "r":
                if paused:
                    pygame.mixer.music.unpause()
                    paused = False
                    print("▶️  Lecture reprise.")
                else:
                    print("La lecture n'est pas en pause.")
            elif cmd == "n" and allow_next_prev:
                pygame.mixer.music.stop()
                print("⏭️  Piste suivante.")
                return "next"
            elif cmd == "p" and allow_next_prev:
                pygame.mixer.music.stop()
                print("⏮️  Piste précédente.")
                return "prev"
            elif cmd == "s":
                pygame.mixer.music.stop()
                print("⛔ Lecture arrêtée.")
                return "stop"
            else:
                if cmd not in ("a", "r", "s", "n", "p"):
                    print("Commande inconnue.")

    except Exception as e:
        print(f" ❌ Impossible de lire le fichier : {e}")
        return "stop"


def play_file(file_path):
    """
    Joue un fichier audio unique en mode interactif.

    Cette fonction encapsule :func:`play_audio_interactive` avec
    ``allow_next_prev=False`` pour désactiver les commandes de navigation
    de playlist.

    Args:
        file_path (str): Chemin du fichier audio à lire.

    Raises:
        SystemExit: Si le fichier n'existe pas.
    """
    print(f"\n{'=' * 60}")
    print(f"Lecture du fichier : {file_path}")
    print(f"{'=' * 60}\n")

    if not os.path.exists(file_path):
        print(f" Le fichier '{file_path}' n'existe pas.")
        sys.exit(1)

    _ = play_audio_interactive(file_path, allow_next_prev=False)
    print("Fin de lecture du fichier.")


def play_playlist(xspf_path):
    """
    Lit une playlist XSPF piste par piste avec contrôle clavier.

    Pour chaque piste, la fonction utilise :func:`play_audio_interactive`
    avec ``allow_next_prev=True`` afin de permettre le contrôle suivant/
    précédent/stop depuis le terminal.

    Args:
        xspf_path (str): Chemin du fichier XSPF à lire.

    Raises:
        SystemExit: Si la playlist n'existe pas ou ne peut pas être
            chargée.
    """
    if not os.path.exists(xspf_path):
        print(f" Le fichier de playlist '{xspf_path}' n'existe pas.")
        sys.exit(1)

    try:
        playlist = load_playlist_from_xspf(xspf_path)
    except Exception as e:
        print(f" Impossible de charger la playlist : {e}")
        sys.exit(1)

    if not playlist or len(playlist) == 0:
        print(" La playlist est vide.")
        return

    print(f"\n{'=' * 60}")
    print(f"Lecture de la playlist : {xspf_path}")
    print(f"{'=' * 60}\n")
    print(f" Nombre de pistes : {len(playlist)}\n")

    index = 0
    while 0 <= index < len(playlist):
        track = playlist[index]
        path = getattr(track, "path", None) or getattr(track, "location", None)

        print(f"\n▶ Piste {index + 1}/{len(playlist)} : {getattr(track, 'title', None) or os.path.basename(path)}")

        action = play_audio_interactive(path, allow_next_prev=True)

        if action in ("next", "end"):
            index += 1
        elif action == "prev":
            index = max(0, index - 1)
        elif action == "stop":
            print(" Arrêt de la lecture de la playlist.")
            break

    print("\nFin de lecture de la playlist.")


# -----------------------------------------------------
#  RECHERCHE EN LIGNE (API MUSICBRAINZ)
# -----------------------------------------------------
def search_online_metadata_cli(file_path: str, max_results: int = 5):
    """
    Recherche des informations en ligne pour un morceau via l'API MusicBrainz.

    Cette fonction lit d'abord les métadonnées locales (titre, artiste) pour
    proposer des valeurs par défaut, puis interroge l'API MusicBrainz et
    affiche les enregistrements trouvés (titre, artistes, album, identifiant).

    Args:
        file_path (str): Chemin du fichier audio servant de base à la
            recherche (pour lire les TAGS locaux).
        max_results (int): Nombre maximal de résultats à afficher.

    Returns:
        None: Les résultats sont affichés directement dans la console.
    """
    print(f"\n{'=' * 60}")
    print(f"Recherche en ligne pour : {file_path}")
    print(f"{'=' * 60}\n")

    # Vérifier le fichier
    try:
        validate_audio_file(file_path)
    except Exception as e:
        print(f"Erreur : {e}")
        return

    # Import de requests (module externe)
    try:
        import requests
    except ImportError:
        print("❌ Cette fonctionnalité nécessite le module 'requests'.")
        print("   Installez-le avec : pip install requests")
        return

    # Lire les métadonnées existantes pour pré-remplir la recherche
    try:
        audio = AudioFile.from_path(file_path)
        md = audio.read_metadata()
        artist_default = md.artist or ""
        title_default = md.title or ""
    except Exception as e:
        print(f"⚠ Impossible de lire les métadonnées locales : {e}")
        artist_default = ""
        title_default = ""

    print("Valeurs détectées dans le fichier :")
    print(f"  Artiste : {artist_default or '(inconnu)'}")
    print(f"  Titre   : {title_default or '(inconnu)'}\n")

    # Permettre à l'utilisateur de modifier/compléter la recherche
    artist = input(f"Artiste pour la recherche [{artist_default}]: ").strip() or artist_default
    title = input(f"Titre pour la recherche   [{title_default}]: ").strip() or title_default

    if not artist and not title:
        print("❌ Aucun critère de recherche fourni. Abandon.")
        return

    print("\n🔍 Recherche en cours sur MusicBrainz...\n")

    # Construire la requête MusicBrainz (comme dans la GUI)
    if artist and title:
        query = f"artist:{artist} AND recording:{title}"
    else:
        query = artist or title

    url = "https://musicbrainz.org/ws/2/recording/"
    params = {
        "query": query,
        "fmt": "json",
        "limit": max_results,
    }

    try:
        resp = requests.get(
            url,
            params=params,
            headers={"User-Agent": "OptiMusicCLI/1.0 (projet universitaire)"},
            timeout=10,
        )
    except Exception as e:
        print(f"❌ Erreur réseau lors de l'appel API : {e}")
        return

    if resp.status_code != 200:
        print(f"❌ Erreur API MusicBrainz : code HTTP {resp.status_code}")
        return

    try:
        data = resp.json()
    except Exception as e:
        print(f"❌ Réponse JSON invalide : {e}")
        return

    recordings = data.get("recordings", [])
    if not recordings:
        print("Aucun résultat trouvé.")
        return

    print(f"✅ {len(recordings)} résultat(s) trouvé(s) (max {max_results}) :\n")

    for i, rec in enumerate(recordings, 1):
        rec_title = rec.get("title", "N/A")
        artists = ", ".join([a.get("name", "") for a in rec.get("artist-credit", [])]) or "N/A"
        releases = rec.get("releases", [])
        album = releases[0].get("title", "N/A") if releases else "N/A"
        rec_id = rec.get("id", "N/A")

        print(f"{i}. {rec_title}")
        print(f"   Artiste(s) : {artists}")
        print(f"   Album      : {album}")
        print(f"   ID         : {rec_id}\n")

    print("Fin de la recherche en ligne.\n")


# -----------------------------------------------------
#  MAIN
# -----------------------------------------------------
def main():
    """
    Point d'entrée principal de la ligne de commande.

    En fonction des arguments fournis, cette fonction délègue le travail
    aux fonctions spécialisées :

    - :func:`display_file_metadata` pour ``-f / --file`` ;
    - :func:`scan_directory` pour ``-d / --directory`` ;
    - :func:`play_file` pour ``-p / --play`` ;
    - :func:`edit_file_metadata` pour ``-e / --edit`` ;
    - :func:`play_playlist` pour ``-P / --play-list`` ;
    - :func:`search_online_metadata_cli` pour ``--api-info``.

    Raises:
        SystemExit: Si aucun argument n'est fourni ou en cas d'option
            non reconnue.
    """
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
    elif args.playlist:
        play_playlist(args.playlist)
    elif args.api_info:
        search_online_metadata_cli(args.api_info)
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
