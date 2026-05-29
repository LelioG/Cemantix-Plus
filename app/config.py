from __future__ import annotations

import os
from pathlib import Path


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent.parent


def build_config() -> dict[str, object]:
    instance_path = Path(os.getenv("CEMANTIX_INSTANCE_PATH", BASE_DIR / "instance"))
    default_db_path = instance_path / "cemantix_plus.sqlite3"
    return {
        "SECRET_KEY": os.getenv("CEMANTIX_SECRET_KEY", "dev-secret-key-change-me"),
        "BASE_DIR": BASE_DIR,
        "INSTANCE_PATH": instance_path,
        "DATABASE_URL": os.getenv("CEMANTIX_DATABASE_URL", f"sqlite:///{default_db_path}"),
        "ENGINE_MODE": os.getenv("CEMANTIX_ENGINE_MODE", "auto").strip().lower(),
        "FASTTEXT_MODEL_PATH": os.getenv(
            "CEMANTIX_FASTTEXT_MODEL_PATH",
            str(BASE_DIR / "data" / "model" / "cc.fr.300.bin"),
        ),
        "FASTTEXT_MODEL_FALLBACK_PATH": str(BASE_DIR / "data" / "models" / "cc.fr.300.bin"),
        "LEXICON_CACHE_PATH": os.getenv(
            "CEMANTIX_LEXICON_CACHE_PATH",
            str(BASE_DIR / "data" / "lexicon" / "fr_lexicon.json"),
        ),
        "LEXICON_SOURCE_PATH": os.getenv(
            "CEMANTIX_LEXICON_SOURCE_PATH",
            str(
                BASE_DIR
                / "data"
                / "sources"
                / "top-open-subtitles-sentences"
                / "bld"
                / "top_words"
                / "fr_top_words.csv"
            ),
        ),
        "DEMO_LEXICON_PATH": os.getenv(
            "CEMANTIX_DEMO_LEXICON_PATH",
            str(BASE_DIR / "data" / "demo_lexicon.json"),
        ),
        "MAX_LEXICON_SIZE": int(os.getenv("CEMANTIX_MAX_LEXICON_SIZE", "25000")),
        "SECRET_POOL_MIN_RANK": int(os.getenv("CEMANTIX_SECRET_POOL_MIN_RANK", "450")),
        "SECRET_POOL_MAX_RANK": int(os.getenv("CEMANTIX_SECRET_POOL_MAX_RANK", "12000")),
        "SECRET_MIN_LENGTH": int(os.getenv("CEMANTIX_SECRET_MIN_LENGTH", "4")),
        "SECRET_MAX_LENGTH": int(os.getenv("CEMANTIX_SECRET_MAX_LENGTH", "14")),
        "MAX_HINTS": int(os.getenv("CEMANTIX_MAX_HINTS", "5")),
        "AUTO_INIT_DB": env_bool("CEMANTIX_AUTO_INIT_DB", True),
        "ALLOW_CUSTOM_MODE": env_bool("CEMANTIX_ALLOW_CUSTOM_MODE", True),
        "LEADERBOARD_LIMIT": int(os.getenv("CEMANTIX_LEADERBOARD_LIMIT", "20")),
        "APP_TITLE": "Cemantix Plus",
    }
