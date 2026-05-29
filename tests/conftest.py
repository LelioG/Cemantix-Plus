from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path: Path):
    database_path = tmp_path / "test.sqlite3"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": f"sqlite:///{database_path}",
            "INSTANCE_PATH": tmp_path / "instance",
            "ENGINE_MODE": "demo",
            "ALLOW_CUSTOM_MODE": True,
            "AUTO_INIT_DB": True,
        }
    )
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
