from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from .api.routes import api_bp
from .config import build_config
from .extensions import db
from .services.game_service import GameService
from .services.lexicon import LexiconService
from .services.semantic import SemanticService
from .web.routes import web_bp


def _use_demo_engine(config: dict[str, object]) -> bool:
    engine_mode = str(config["ENGINE_MODE"]).strip().lower()
    if engine_mode == "demo":
        return True
    if engine_mode == "fasttext":
        return False
    primary = Path(str(config["FASTTEXT_MODEL_PATH"]))
    fallback = Path(str(config["FASTTEXT_MODEL_FALLBACK_PATH"]))
    return not primary.exists() and not fallback.exists()


def create_app(test_config: dict[str, object] | None = None) -> Flask:
    load_dotenv()

    app = Flask(__name__, instance_relative_config=False)
    app.config.update(build_config())
    if test_config:
        app.config.update(test_config)

    Path(str(app.config["INSTANCE_PATH"])).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    if app.config.get("AUTO_INIT_DB", True):
        db.ensure_schema()

    demo_mode = _use_demo_engine(app.config)
    lexicon = LexiconService(app.config, demo_mode=demo_mode)
    semantic = SemanticService(app.config, lexicon)
    game_service = GameService(app.config, db, lexicon, semantic)
    app.extensions["lexicon_service"] = lexicon
    app.extensions["semantic_service"] = semantic
    app.extensions["game_service"] = game_service

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    return app
