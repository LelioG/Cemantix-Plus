from __future__ import annotations

from pathlib import Path

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker


class Database:
    def __init__(self) -> None:
        self.engine: Engine | None = None
        self.Session = scoped_session(sessionmaker(autoflush=False, expire_on_commit=False))

    def init_app(self, app: Flask) -> None:
        database_url = app.config["DATABASE_URL"]
        connect_args: dict[str, object] = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            db_path = database_url.removeprefix("sqlite:///")
            if db_path and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(database_url, future=True, connect_args=connect_args)
        self.Session.configure(bind=self.engine)
        app.extensions["db"] = self

        @app.teardown_appcontext
        def remove_session(_exception: BaseException | None = None) -> None:
            self.Session.remove()

    @property
    def session(self):
        return self.Session

    def ensure_schema(self) -> None:
        from .models import Base

        if self.engine is None:
            raise RuntimeError("Database engine is not initialized.")
        Base.metadata.create_all(self.engine)


db = Database()
