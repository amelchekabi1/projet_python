
# Gestionnaire de Bibliothèque Musicale

## 👥 Membres du projet

- **HASSANI Maria** - Groupe D
- **CHEKABI Amel** - Groupe B
- **OUARET Islam** - Groupe B

**Année universitaire** : 2025-2026  
**Formation** : Licence 3 Informatique  
**Module** : Mineure Python - Projet

---

##  Description

Application Python de gestion de bibliothèque musicale permettant l'analyse, l'organisation et la lecture de fichiers audio MP3 et FLAC avec interface en ligne de commande (CLI) et interface graphique (GUI).

### Fonctionnalités principales

-  Extraction et affichage des métadonnées (ID3 pour MP3, Vorbis Comment pour FLAC)
-  Exploration récursive de dossiers avec filtrage par extension et type MIME
-  Création et gestion de playlists au format XSPF (standard XML)
-  Lecture audio intégrée (pygame/QtMultimedia)
-  Édition des métadonnées (tags ID3/Vorbis)
-  Gestion des couvertures d'albums (extraction, affichage, téléchargement)
-  Recherche via API web pour infos complètes d'albums et paroles
-  Interface graphique intuitive

### Deux modes de fonctionnement

Mode CLI : Interface en ligne de commande rapide et scriptable
Mode GUI : Interface graphique conviviale avec PySide6
---

## 🔧 Prérequis

- **Python** 3.8 ou supérieur
- **Système d'exploitation** : Linux, macOS ou Windows

---

##  Installation

### 1. Récupérer le projet

```bash
# Si vous avez Git
git clone [URL_DU_DEPOT]
cd HASSANI_CHEKABI_OUARET

```

### 2. Créer un environnement virtuel (recommandé)

```bash
# Créer l'environnement
python3 -m venv venv


### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

**Dépendances principales :**
- `mutagen` : extraction et modification des métadonnées
- `python-magic` : vérification des types MIME
- `pygame` : lecture audio
- `Pillow` : gestion des images
- `requests` : requêtes API web

**Note** : Sur certains systèmes, des bibliothèques supplémentaires peuvent être nécessaires :

```bash
# Linux
sudo apt-get install libmagic1

# macOS
brew install libmagic

# Windows
pip install python-magic-bin
```

---

##  Utilisation

### Mode CLI (Console)

#### Afficher l'aide

```bash
python3 cli/cli.py -h
```

#### Analyser un fichier

Affiche les métadonnées d'un fichier MP3 ou FLAC :

```bash
python3 cli/cli.py -f chemin/vers/musique.mp3
```

**Exemple de sortie :**
```
============================================================
Analyse du fichier : musique.mp3
============================================================

 Informations du fichier :
  - Nom : musique.mp3
  - Taille : 5242880 octets
  - Format : MP3

 Métadonnées :
  - Titre : Bohemian Rhapsody
  - Artiste : Queen
  - Album : A Night at the Opera
  - Durée : 354 secondes
  - Année : 1975
```

#### Scanner un dossier

Parcourt récursivement un dossier et liste tous les fichiers MP3/FLAC :

```bash
python3 cli/cli.py -d chemin/vers/musique/
```

#### Créer une playlist

Scanner un dossier et générer une playlist XSPF :

```bash
python3 cli/cli.py -d ./musique/ -o ma_playlist.xspf
```

La playlist générée peut être validée sur : https://validator.xspf.org/

#### Jouer un morceau

```bash
python3 cli/cli.py -p chemin/vers/musique.mp3
```

### Mode GUI (Interface graphique)

```bash
python3 src/gui.py
```

L'interface graphique permet de :
-  Naviguer dans l'arborescence de vos dossiers
-  Visualiser les métadonnées de chaque fichier
-  Créer des playlists personnalisées par glisser-déposer
-  Modifier les TAGS des morceaux
-  Afficher et gérer les pochettes d'albums
-  Écouter vos morceaux et playlists

---

##  Structure du projet

```
HASSANI_CHEKABI_OUARET/
├── cli/
│   └── cli.py                  # Programme principal (entrée CLI)
├── gui/
│   └── music_manager_gui.py
├── library/
│   ├── audiofile.py            # Gestion MP3/FLAC et métadonnées
│   ├── directory_scanner.py    # Exploration récursive du dossier
│   ├── playlist.py             # Gestion d'une playlist (liste de fichiers)
│   └── xspf_writer.py          # Génération du fichier playlist.xspf
    └── validation.py           
├── doc/
│   ├── diaporama/              # Présentation de soutenance
│   ├── documentation/          # Documentation technique (Doxygen)
│   └── rapport/                # Rapport de projet (ODT + PDF)
├── tests/                      # Tests unitaires
├── requirements.txt            # Dépendances Python
└── README.md                   # Ce fichier
```

---

##  Fonctionnalités

###  Fonctionnalités implémentées

**Mode CLI :**
- [x] Parsing des arguments en ligne de commande
- [x] Extraction des métadonnées MP3/FLAC
- [x] Exploration récursive de dossiers
- [x] Génération de playlist XSPF
- [x] Lecture audio
- [x] Gestion des erreurs

**Mode GUI :**
- [ ] Interface graphique (en cours)
- [ ] Navigation dans l'arborescence
- [ ] Affichage des métadonnées
- [ ] Création de playlists personnalisées
- [ ] Extraction/affichage des pochettes
- [ ] Édition des TAGS
- [ ] Intégration API web


---


##  Tests

Pour exécuter les tests unitaires :

```bash
python3 -m pytest tests/ -v
```

Pour générer un rapport de couverture :

```bash
python3 -m pytest --cov=library tests/
```

---



## 📹 Démonstration

Une vidéo de démonstration (5 minutes maximum) présentant toutes les fonctionnalités sera disponible avant le 11 décembre 2025.

---

## 📅 Planning

- **5 octobre** : Constitution du trinôme
- **17 octobre** : Diagramme de Gantt
- **7 novembre** : Point d'avancement 1 (50% attendu)
- **28 novembre** : Point d'avancement 2
- **11 décembre** : Dépôt vidéo de démonstration
- **12 décembre** : Dépôt final du projet
- **19 décembre** : Soutenance (15 min)

---

## 📄 Licence

Projet académique - Université Cergy-Pontoise - Année 2025-2026

Ce projet est réalisé dans le cadre du module « Mineure Python » de la Licence 3 Informatique.

---

## 🙏 Remerciements

- Enseignants du module Python pour leur accompagnement
- Documentation officielle : Mutagen, Pygame, XSPF
- Communauté Python

---
