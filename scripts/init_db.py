from __future__ import annotations

from pathlib import Path

import _bootstrap  # noqa: F401
from alembic import command
from alembic.config import Config as AlembicConfig
from dotenv import load_dotenv

from app.config import build_config


def main() -> None:
    load_dotenv()
    runtime_config = build_config()
    Path(str(runtime_config["INSTANCE_PATH"])).mkdir(parents=True, exist_ok=True)

    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(runtime_config["DATABASE_URL"]))
    command.upgrade(alembic_cfg, "head")
    print(f"Base SQLite prête: {runtime_config['DATABASE_URL']}")


if __name__ == "__main__":
    main()
