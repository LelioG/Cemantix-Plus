from __future__ import annotations

import os

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("CEMANTIX_HOST", "127.0.0.1"),
        port=int(os.getenv("CEMANTIX_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"},
    )
