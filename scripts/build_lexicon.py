from __future__ import annotations

import _bootstrap  # noqa: F401
from dotenv import load_dotenv

from app.config import build_config
from app.services.lexicon import LexiconService


def main() -> None:
    load_dotenv()
    config = build_config()
    service = LexiconService(config, demo_mode=False)
    print(f"Lexique généré: {len(service.words)} mots")
    print(f"Secrets candidats: {len(service.secret_words)}")
    print(f"Cache: {config['LEXICON_CACHE_PATH']}")


if __name__ == "__main__":
    main()
