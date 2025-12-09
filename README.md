
# Gestionnaire de Bibliothèque Musicale

## 👥 Membres du projet

- **HASSANI Maria** - Groupe D
- **CHEKABI Amel** - Groupe B
- **OUARET Islam** - Groupe B

**Année universitaire** : 2025-2026  
**Formation** : Licence 3 Informatique  
**Module** : Mineure Python - Projet

---

## 📖 Description

Application Python de gestion de bibliothèque musicale permettant l'analyse, l'organisation et la lecture de fichiers audio MP3 et FLAC.

### Fonctionnalités principales

- 🔍 Extraction et affichage des métadonnées (ID3 pour MP3, Vorbis pour FLAC)
- 📁 Exploration récursive de dossiers contenant des fichiers musicaux
- 📋 Création et gestion de playlists au format XSPF
- 🎵 Lecture de morceaux audio
- ✏️ Édition des métadonnées (TAGS)
- 🖼️ Gestion des pochettes d'albums

### Deux modes de fonctionnement

- **Mode CLI** : Interface en ligne de commande pour une utilisation rapide et scriptable
- **Mode GUI** : Interface graphique intuitive pour une expérience utilisateur conviviale

---

## 🔧 Prérequis

- **Python** 3.8 ou supérieur
- **Système d'exploitation** : Linux, macOS ou Windows

---

## 📦 Installation

### 1. Récupérer le projet

```bash
# Si vous avez Git
git clone [URL_DU_DEPOT]
cd NOM1_NOM2_NOM3

# Ou décompresser l'archive
unzip NOM1_NOM2_NOM3.zip
cd NOM1_NOM2_NOM3
```

### 2. Créer un environnement virtuel (recommandé)

```bash
# Créer l'environnement
python3 -m venv venv

# L'activer
source venv/bin/activate          # Linux/macOS
venv\Scripts\activate             # Windows
```

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

## 🚀 Utilisation

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

📁 Informations du fichier :
  - Nom : musique.mp3
  - Taille : 5242880 octets
  - Format : MP3

🎵 Métadonnées :
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
- 📂 Naviguer dans l'arborescence de vos dossiers
- 👀 Visualiser les métadonnées de chaque fichier
- 🎨 Créer des playlists personnalisées par glisser-déposer
- ✏️ Modifier les TAGS des morceaux
- 🖼️ Afficher et gérer les pochettes d'albums
- 🎵 Écouter vos morceaux et playlists

---

## 📂 Structure du projet

```
NOM1_NOM2_NOM3/
├── cli/
│   └── cli.py                  # Programme principal (entrée CLI)
├── library/
│   ├── audiofile.py            # Gestion MP3/FLAC et métadonnées
│   ├── directory_scanner.py    # Exploration récursive du dossier
│   ├── playlist.py             # Gestion d'une playlist (liste de fichiers)
│   └── xspf_writer.py          # Génération du fichier playlist.xspf
├── doc/
│   ├── diaporama/              # Présentation de soutenance
│   ├── documentation/          # Documentation technique (Doxygen)
│   └── rapport/                # Rapport de projet (ODT + PDF)
├── tests/                      # Tests unitaires
├── requirements.txt            # Dépendances Python
└── README.md                   # Ce fichier
```

---

## ⚙️ Fonctionnalités

### ✅ Fonctionnalités implémentées

**Mode CLI :**
- [x] Parsing des arguments en ligne de commande
- [x] Extraction des métadonnées MP3/FLAC
- [x] Exploration récursive de dossiers
- [x] Filtrage par extension et type MIME
- [x] Génération de playlist XSPF
- [x] Lecture audio
- [x] Gestion des erreurs

**Mode GUI :**
- [ ] Interface graphique (en cours)
- [ ] Navigation dans l'arborescence
- [ ] Affichage des métadonnées
- [ ] Création de playlists personnalisées
- [ ] Drag & Drop de fichiers
- [ ] Extraction/affichage des pochettes
- [ ] Édition des TAGS
- [ ] Intégration API web

### 🚧 Extensions possibles

- [ ] Import/Export de playlists M3U
- [ ] Normalisation audio
- [ ] Détection automatique des doublons
- [ ] Statistiques de la bibliothèque

---

## 🔑 Points techniques

### Formats audio supportés

- **MP3** (MPEG Audio Layer 3)
  - Métadonnées : ID3v1, ID3v2.3, ID3v2.4
  - Type MIME : `audio/mpeg`

- **FLAC** (Free Lossless Audio Codec)
  - Métadonnées : Vorbis Comment
  - Type MIME : `audio/flac`, `audio/x-flac`

### Format de playlist

**XSPF** (XML Shareable Playlist Format)
- Standard ouvert : https://xspf.org/
- Validation en ligne : https://validator.xspf.org/

### Validation des fichiers

Le programme effectue une double vérification :
1. **Extension** : `.mp3` ou `.flac`
2. **Type MIME** : vérification du contenu réel du fichier

Cela évite les faux fichiers (ex: un `.txt` renommé en `.mp3`).

---

## 🐛 Problèmes connus et solutions

### Erreur : "No module named 'magic'"

**Solution :**
```bash
pip install python-magic
# Si Windows :
pip install python-magic-bin
```

### Erreur : "pygame.error: No available audio device"

**Solution :** Vérifiez que votre système dispose d'une carte son fonctionnelle et que les pilotes audio sont installés.

### La playlist ne s'ouvre pas dans mon lecteur

**Solution :** Validez d'abord votre fichier XSPF sur https://validator.xspf.org/ pour identifier les erreurs de format.

---

## 🧪 Tests

Pour exécuter les tests unitaires :

```bash
python3 -m pytest tests/ -v
```

Pour générer un rapport de couverture :

```bash
python3 -m pytest --cov=library tests/
```

---

## 📚 Documentation

La documentation complète du code est disponible dans `doc/documentation/` :

- **Format Doxygen** : consultez `doc/documentation/html/index.html`
- **Docstrings Python** : chaque fonction est documentée dans le code

Pour générer la documentation :

```bash
doxygen Doxyfile
```

---

## 📹 Démonstration

Une vidéo de démonstration (5 minutes maximum) présentant toutes les fonctionnalités sera disponible avant le 11 décembre 2025.

---

## 👨‍💻 Répartition des tâches

| Membre | Responsabilités |
|--------|----------------|
| **Personne 1** | CLI (cli.py), README.md, documentation |
| **Personne 2** | Modules library (audiofile.py, directory_scanner.py) |
| **Personne 3** | Modules library (playlist.py, xspf_writer.py) |
| **Tous** | Tests, intégration, rapport, soutenance |

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

Projet académique - Université [NOM] - Année 2025-2026

Ce projet est réalisé dans le cadre du module « Mineure Python » de la Licence 3 Informatique.

---

## 🙏 Remerciements

- Enseignants du module Python pour leur accompagnement
- Documentation officielle : Mutagen, Pygame, XSPF
- Communauté Python et forums d'entraide

---

## 📞 Contact

Pour toute question concernant ce projet :

- **Email** : prenom.nom@etudiant.universite.fr
- **Dépôt Git** : [URL si applicable]

---


# Gestionnaire de Bibliothèque Musicale

## 👥 Membres du projet

- **HASSANI Maria** - Groupe D
- **CHEKABI Amel** - Groupe B
- **OUARET Islam** - Groupe B

**Année universitaire** : 2025-2026  
**Formation** : Licence 3 Informatique  
**Module** : Mineure Python - Projet

---

## 📖 Description

Application Python de gestion de bibliothèque musicale permettant l'analyse, l'organisation et la lecture de fichiers audio MP3 et FLAC.

### Fonctionnalités principales

- 🔍 Extraction et affichage des métadonnées (ID3 pour MP3, Vorbis pour FLAC)
- 📁 Exploration récursive de dossiers contenant des fichiers musicaux
- 📋 Création et gestion de playlists au format XSPF
- 🎵 Lecture de morceaux audio
- ✏️ Édition des métadonnées (TAGS)
- 🖼️ Gestion des pochettes d'albums

### Deux modes de fonctionnement

- **Mode CLI** : Interface en ligne de commande pour une utilisation rapide et scriptable
- **Mode GUI** : Interface graphique intuitive pour une expérience utilisateur conviviale

---

## 🔧 Prérequis

- **Python** 3.8 ou supérieur
- **Système d'exploitation** : Linux, macOS ou Windows

---

## 📦 Installation

### 1. Récupérer le projet

```bash
# Si vous avez Git
git clone [URL_DU_DEPOT]
cd NOM1_NOM2_NOM3

# Ou décompresser l'archive
unzip NOM1_NOM2_NOM3.zip
cd NOM1_NOM2_NOM3
```

### 2. Créer un environnement virtuel (recommandé)

```bash
# Créer l'environnement
python3 -m venv venv

# L'activer
source venv/bin/activate          # Linux/macOS
venv\Scripts\activate             # Windows
```

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

## 🚀 Utilisation

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

📁 Informations du fichier :
  - Nom : musique.mp3
  - Taille : 5242880 octets
  - Format : MP3

🎵 Métadonnées :
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
- 📂 Naviguer dans l'arborescence de vos dossiers
- 👀 Visualiser les métadonnées de chaque fichier
- 🎨 Créer des playlists personnalisées par glisser-déposer
- ✏️ Modifier les TAGS des morceaux
- 🖼️ Afficher et gérer les pochettes d'albums
- 🎵 Écouter vos morceaux et playlists

---

## 📂 Structure du projet

```
NOM1_NOM2_NOM3/
├── cli/
│   └── cli.py                  # Programme principal (entrée CLI)
├── library/
│   ├── audiofile.py            # Gestion MP3/FLAC et métadonnées
│   ├── directory_scanner.py    # Exploration récursive du dossier
│   ├── playlist.py             # Gestion d'une playlist (liste de fichiers)
│   └── xspf_writer.py          # Génération du fichier playlist.xspf
├── doc/
│   ├── diaporama/              # Présentation de soutenance
│   ├── documentation/          # Documentation technique (Doxygen)
│   └── rapport/                # Rapport de projet (ODT + PDF)
├── tests/                      # Tests unitaires
├── requirements.txt            # Dépendances Python
└── README.md                   # Ce fichier
```

---

## ⚙️ Fonctionnalités

### ✅ Fonctionnalités implémentées

**Mode CLI :**
- [x] Parsing des arguments en ligne de commande
- [x] Extraction des métadonnées MP3/FLAC
- [x] Exploration récursive de dossiers
- [x] Filtrage par extension et type MIME
- [x] Génération de playlist XSPF
- [x] Lecture audio
- [x] Gestion des erreurs

**Mode GUI :**
- [ ] Interface graphique (en cours)
- [ ] Navigation dans l'arborescence
- [ ] Affichage des métadonnées
- [ ] Création de playlists personnalisées
- [ ] Drag & Drop de fichiers
- [ ] Extraction/affichage des pochettes
- [ ] Édition des TAGS
- [ ] Intégration API web

### 🚧 Extensions possibles

- [ ] Import/Export de playlists M3U
- [ ] Normalisation audio
- [ ] Détection automatique des doublons
- [ ] Statistiques de la bibliothèque

---

## 🔑 Points techniques

### Formats audio supportés

- **MP3** (MPEG Audio Layer 3)
  - Métadonnées : ID3v1, ID3v2.3, ID3v2.4
  - Type MIME : `audio/mpeg`

- **FLAC** (Free Lossless Audio Codec)
  - Métadonnées : Vorbis Comment
  - Type MIME : `audio/flac`, `audio/x-flac`

### Format de playlist

**XSPF** (XML Shareable Playlist Format)
- Standard ouvert : https://xspf.org/
- Validation en ligne : https://validator.xspf.org/

### Validation des fichiers

Le programme effectue une double vérification :
1. **Extension** : `.mp3` ou `.flac`
2. **Type MIME** : vérification du contenu réel du fichier

Cela évite les faux fichiers (ex: un `.txt` renommé en `.mp3`).

---

## 🐛 Problèmes connus et solutions

### Erreur : "No module named 'magic'"

**Solution :**
```bash
pip install python-magic
# Si Windows :
pip install python-magic-bin
```

### Erreur : "pygame.error: No available audio device"

**Solution :** Vérifiez que votre système dispose d'une carte son fonctionnelle et que les pilotes audio sont installés.

### La playlist ne s'ouvre pas dans mon lecteur

**Solution :** Validez d'abord votre fichier XSPF sur https://validator.xspf.org/ pour identifier les erreurs de format.

---

## 🧪 Tests

Pour exécuter les tests unitaires :

```bash
python3 -m pytest tests/ -v
```

Pour générer un rapport de couverture :

```bash
python3 -m pytest --cov=library tests/
```

---

## 📚 Documentation

La documentation complète du code est disponible dans `doc/documentation/` :

- **Format Doxygen** : consultez `doc/documentation/html/index.html`
- **Docstrings Python** : chaque fonction est documentée dans le code

Pour générer la documentation :

```bash
doxygen Doxyfile
```

---

## 📹 Démonstration

Une vidéo de démonstration (5 minutes maximum) présentant toutes les fonctionnalités sera disponible avant le 11 décembre 2025.

---

## 👨‍💻 Répartition des tâches

| Membre | Responsabilités |
|--------|----------------|
| **Personne 1** | CLI (cli.py), README.md, documentation |
| **Personne 2** | Modules library (audiofile.py, directory_scanner.py) |
| **Personne 3** | Modules library (playlist.py, xspf_writer.py) |
| **Tous** | Tests, intégration, rapport, soutenance |

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

Projet académique - Université [NOM] - Année 2025-2026

Ce projet est réalisé dans le cadre du module « Mineure Python » de la Licence 3 Informatique.

---

## 🙏 Remerciements

- Enseignants du module Python pour leur accompagnement
- Documentation officielle : Mutagen, Pygame, XSPF
- Communauté Python et forums d'entraide

---

## 📞 Contact

Pour toute question concernant ce projet :

- **Email** : prenom.nom@etudiant.universite.fr
- **Dépôt Git** : [URL si applicable]

---

>>>>>>> 9660236 (Add files via upload)
*Dernière mise à jour : Octobre 2025*