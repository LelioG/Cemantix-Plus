# Cemantix Plus

Application web complète de type Cemantix en français, construite avec Flask, SQLAlchemy, SQLite et fastText.

Le projet est maintenant jouable de bout en bout en local avec:

- moteur sémantique fastText français réel
- validation via whitelist de vocabulaire
- normalisation linguistique
- base SQLite persistante
- migrations Alembic
- modes `daily`, `infinite`, `custom dev`
- indices progressifs persistants
- stats par partie et globales
- leaderboard
- UI responsive moderne
- routes HTML + API JSON propres
- scripts utilitaires
- tests `pytest`
- configuration par variables d’environnement

## Architecture

```text
cemantix_plus/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── api/routes.py
│   ├── web/routes.py
│   ├── services/
│   │   ├── game_service.py
│   │   ├── lexicon.py
│   │   └── semantic.py
│   ├── utils/text.py
│   ├── templates/index.html
│   └── static/
│       ├── app.js
│       └── style.css
├── data/
│   ├── demo_lexicon.json
│   ├── model/cc.fr.300.bin                         # via Google Drive
│   ├── lexicon/...                                  # via Google Drive
│   └── sources/top-open-subtitles-sentences/...     # via Google Drive
├── migrations/
├── scripts/
│   ├── init_db.py
│   ├── build_lexicon.py
│   └── seed_daily.py
├── tests/
├── alembic.ini
├── .env.example
├── requirements.txt
└── run.py
```

## Moteur sémantique

### Mode principal

Par défaut, l’application utilise le modèle fastText français présent dans:

`data/model/cc.fr.300.bin`

Le dépôt contient seulement `data/demo_lexicon.json`, utilisé pour le mode démo.
Le dossier `data/` complet n’est pas versionné car il est trop volumineux.
Il peut être téléchargé ici:

https://drive.google.com/drive/folders/1dydjO0r1Dlwx3DlgPeRhCq8i8wHSvrlk?usp=sharing

Après téléchargement, remplacer ou compléter le dossier `data/` à la racine du projet.

Le score d’une proposition est calculé via cosinus entre le vecteur du mot proposé et le vecteur du mot secret.

### Validation vocabulaire

Les mots proposés ne sont pas acceptés via les subwords fastText seuls.
Ils doivent d’abord appartenir au lexique whitelist chargé depuis:

`data/sources/top-open-subtitles-sentences/bld/top_words/fr_top_words.csv`

Le cache généré est écrit dans:

`data/lexicon/fr_lexicon.json`

### Fallback dev

Si le modèle fastText manque ou si `CEMANTIX_ENGINE_MODE=demo`, l’application bascule sur le mini lexique `data/demo_lexicon.json`, qui est inclus dans le dépôt.

## Base de données

Tables principales:

- `users`
- `games`
- `guesses`
- `daily_words`
- `hints`
- `leaderboard_entries`

La base SQLite par défaut est:

`instance/cemantix_plus.sqlite3`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
cd /home/lgualino/Documents/cemantix_plus
pip install -r requirements.txt
```

### Données et modèle fastText

Pour utiliser le moteur sémantique complet, télécharger le dossier `data/` depuis Google Drive:

https://drive.google.com/drive/folders/1dydjO0r1Dlwx3DlgPeRhCq8i8wHSvrlk?usp=sharing

Puis placer ce dossier à la racine du projet:

```text
data/
```

Sans le dossier `data/` complet, seule la version démo fonctionne avec `CEMANTIX_ENGINE_MODE=demo`.

## Initialisation

1. Générer le cache de lexique:

```bash
python scripts/build_lexicon.py
```

2. Appliquer les migrations:

```bash
python scripts/init_db.py
```

3. Optionnel: pré-générer les mots daily:

```bash
python scripts/seed_daily.py --days 30
```

## Lancement

```bash
python run.py
```

Puis ouvrir:

`http://127.0.0.1:5000`

## Configuration

Variables principales:

- `CEMANTIX_DATABASE_URL`
- `CEMANTIX_SECRET_KEY`
- `CEMANTIX_ENGINE_MODE=auto|fasttext|demo`
- `CEMANTIX_FASTTEXT_MODEL_PATH`
- `CEMANTIX_LEXICON_CACHE_PATH`
- `CEMANTIX_LEXICON_SOURCE_PATH`
- `CEMANTIX_MAX_LEXICON_SIZE`
- `CEMANTIX_SECRET_POOL_MIN_RANK`
- `CEMANTIX_SECRET_POOL_MAX_RANK`
- `CEMANTIX_SECRET_MIN_LENGTH`
- `CEMANTIX_SECRET_MAX_LENGTH`
- `CEMANTIX_MAX_HINTS`
- `CEMANTIX_ALLOW_CUSTOM_MODE`
- `CEMANTIX_AUTO_INIT_DB`
- `CEMANTIX_HOST`
- `CEMANTIX_PORT`
- `FLASK_DEBUG`

Copie `.env.example` vers `.env` si besoin.

## API principale

HTML:

- `GET /`
- `GET /leaderboard`

JSON:

- `GET /api/v1/bootstrap`
- `POST /api/v1/game/select`
- `POST /api/v1/game/guess`
- `POST /api/v1/game/hint`
- `GET /api/v1/leaderboard`
- `GET /api/v1/stats`
- `PUT /api/v1/profile`
- `GET /api/v1/health`

## Tests

Les tests tournent en mode démo rapide, sans charger le modèle fastText complet:

```bash
pytest
```

## Notes de fonctionnement

- le mode `daily` donne le même mot à tout le monde pour une date donnée
- le mode `infinite` crée un nouveau mot aléatoire du pool de secrets
- le mode `custom dev` permet de forcer un mot secret du lexique whitelist
- les scores et hints sont persistés en base
- le leaderboard enregistre les parties gagnées
- l’application auto-crée le schéma si `CEMANTIX_AUTO_INIT_DB=true`, mais les migrations Alembic restent fournies et prêtes pour l’évolution du schéma


  cd /home/lgualino/Documents/cemantix_plus
  source .venv/bin/activate
  python scripts/build_lexicon.py
  python scripts/init_db.py
  python scripts/seed_daily.py --days 30
  python run.py
