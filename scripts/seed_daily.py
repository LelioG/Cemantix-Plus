from __future__ import annotations

import argparse
from datetime import date, timedelta

import _bootstrap  # noqa: F401
from app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Pré-génère des mots daily dans la base.")
    parser.add_argument("--days", type=int, default=14, help="Nombre de jours à seed à partir d'aujourd'hui.")
    args = parser.parse_args()

    app = create_app()
    service = app.extensions["game_service"]
    with app.app_context():
        for offset in range(args.days):
            target_date = date.today() + timedelta(days=offset)
            daily_word = service._get_or_create_daily_word(target_date)
            print(target_date.isoformat(), daily_word.word)


if __name__ == "__main__":
    main()
