from __future__ import annotations

from app.services.lexicon import LexiconService


def test_lexicon_resolves_ascii_alias(app):
    service = LexiconService(app.config, demo_mode=True)
    assert service.resolve("coeur").word == "cœur"
