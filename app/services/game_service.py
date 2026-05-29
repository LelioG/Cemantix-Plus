from __future__ import annotations

import secrets
from datetime import date
from typing import Any

from sqlalchemy import Select, func, select

from ..models import DailyWord, Game, Guess, Hint, LeaderboardEntry, User
from ..utils.dates import utcnow
from ..utils.text import normalize_word


SUPPORTED_MODES = {"daily", "infinite", "custom"}


class GameService:
    def __init__(self, config: dict[str, Any], db, lexicon, semantic) -> None:
        self.config = config
        self.db = db
        self.lexicon = lexicon
        self.semantic = semantic

    def bootstrap(self, session_obj, requested_mode: str | None = None) -> dict[str, Any]:
        user = self.get_or_create_user(session_obj)
        mode = self._resolve_mode(requested_mode or session_obj.get("current_mode"))
        try:
            game = self.get_or_create_game(user, mode)
        except ValueError:
            mode = "daily"
            game = self.get_or_create_game(user, mode)
        session_obj["current_mode"] = mode
        return {
            "ok": True,
            "user": self.serialize_user(user),
            "current_mode": mode,
            "game": self.serialize_game(game),
            "stats": self.serialize_stats(user),
            "leaderboard": self.serialize_leaderboard(mode, self._leaderboard_date(game)),
            "engine": self.semantic.engine_meta(),
            "modes": self.available_modes(),
        }

    def available_modes(self) -> dict[str, bool]:
        return {
            "daily": True,
            "infinite": True,
            "custom": bool(self.config["ALLOW_CUSTOM_MODE"]),
        }

    def get_or_create_user(self, session_obj) -> User:
        public_id = session_obj.get("user_public_id")
        db_session = self.db.session
        user = None
        if public_id:
            user = db_session.execute(
                select(User).where(User.public_id == public_id)
            ).scalar_one_or_none()
        if user is None:
            public_id = secrets.token_urlsafe(12)
            user = User(
                public_id=public_id,
                display_name=f"Explorateur-{public_id[:4].upper()}",
            )
            db_session.add(user)
            db_session.commit()
            session_obj["user_public_id"] = public_id
        user.last_seen_at = utcnow()
        db_session.commit()
        return user

    def update_profile(self, session_obj, display_name: str) -> dict[str, Any]:
        user = self.get_or_create_user(session_obj)
        cleaned = " ".join((display_name or "").strip().split())
        if len(cleaned) < 2 or len(cleaned) > 24:
            return {"ok": False, "error": "Le pseudo doit contenir entre 2 et 24 caractères."}
        user.display_name = cleaned
        self.db.session.commit()
        return {"ok": True, "user": self.serialize_user(user)}

    def select_game(
        self,
        session_obj,
        mode: str,
        *,
        new_game: bool = False,
        custom_word: str | None = None,
    ) -> dict[str, Any]:
        user = self.get_or_create_user(session_obj)
        mode = self._resolve_mode(mode)
        try:
            game = self.get_or_create_game(user, mode, new_game=new_game, custom_word=custom_word)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        session_obj["current_mode"] = mode
        return {
            "ok": True,
            "current_mode": mode,
            "game": self.serialize_game(game),
            "stats": self.serialize_stats(user),
            "leaderboard": self.serialize_leaderboard(mode, self._leaderboard_date(game)),
        }

    def process_guess(self, session_obj, raw_word: str) -> dict[str, Any]:
        user = self.get_or_create_user(session_obj)
        game = self.get_current_game(session_obj, user)
        if game.won:
            return {"ok": False, "error": "Cette partie est déjà terminée."}

        entry = self.lexicon.resolve(raw_word)
        if entry is None:
            return {"ok": False, "error": "Mot inconnu dans le vocabulaire français autorisé."}

        db_session = self.db.session
        duplicate = db_session.execute(
            select(Guess).where(
                Guess.game_id == game.id,
                Guess.normalized_word == entry.normalized,
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            return {"ok": False, "error": "Ce mot a déjà été proposé dans cette partie."}

        result = self.semantic.score_guess(entry.word, game.secret_word)
        guess = Guess(
            game_id=game.id,
            attempt_number=game.attempts_count + 1,
            word=result["word"],
            normalized_word=normalize_word(result["word"]),
            score=result["score"],
            percentile=result["percentile"],
            semantic_rank=result["semantic_rank"],
            temperature=result["temperature"],
            is_exact=result["exact"],
        )
        db_session.add(guess)
        game.attempts_count += 1
        game.best_score = max(game.best_score, result["score"])
        game.last_played_at = utcnow()
        if result["exact"]:
            game.won = True
            game.status = "won"
            game.ended_at = utcnow()
            self._upsert_leaderboard_entry(game)
        db_session.commit()

        return {
            "ok": True,
            "entry": self.serialize_guess(guess),
            "game": self.serialize_game(game),
            "stats": self.serialize_stats(user),
            "leaderboard": self.serialize_leaderboard(game.mode, self._leaderboard_date(game)),
            "message": (
                f"Trouvé: « {game.secret_word} »."
                if result["exact"]
                else f"{result['word']} est {result['temperature'].lower()}."
            ),
        }

    def request_hint(self, session_obj) -> dict[str, Any]:
        user = self.get_or_create_user(session_obj)
        game = self.get_current_game(session_obj, user)
        if game.won:
            return {"ok": False, "error": "La partie est déjà gagnée."}
        if len(game.hints) >= int(self.config["MAX_HINTS"]):
            return {"ok": False, "error": "Tous les indices disponibles ont déjà été révélés."}

        hint_type, content = self.semantic.build_hint_sequence(game.secret_word)[len(game.hints)]
        hint = Hint(
            game_id=game.id,
            level=len(game.hints) + 1,
            hint_type=hint_type,
            content=content,
        )
        self.db.session.add(hint)
        game.hints_used += 1
        game.last_played_at = utcnow()
        self.db.session.commit()
        self.db.session.refresh(game)

        return {
            "ok": True,
            "hint": self.serialize_hint(hint),
            "game": self.serialize_game(game),
            "stats": self.serialize_stats(user),
        }

    def get_stats_payload(self, session_obj) -> dict[str, Any]:
        user = self.get_or_create_user(session_obj)
        game = self.get_current_game(session_obj, user)
        return {
            "ok": True,
            "stats": self.serialize_stats(user),
            "game": self.serialize_game(game),
        }

    def get_leaderboard_payload(
        self,
        session_obj,
        mode: str | None = None,
        on_date: date | None = None,
    ) -> dict[str, Any]:
        user = self.get_or_create_user(session_obj)
        current_mode = self._resolve_mode(mode or session_obj.get("current_mode"))
        return {
            "ok": True,
            "leaderboard": self.serialize_leaderboard(current_mode, on_date),
            "stats": self.serialize_stats(user),
        }

    def get_health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "engine": self.semantic.engine_meta(),
            "database_url": self.config["DATABASE_URL"],
            "custom_mode": bool(self.config["ALLOW_CUSTOM_MODE"]),
        }

    def get_current_game(self, session_obj, user: User) -> Game:
        mode = self._resolve_mode(session_obj.get("current_mode"))
        game = self.get_or_create_game(user, mode)
        session_obj["current_mode"] = mode
        return game

    def get_or_create_game(
        self,
        user: User,
        mode: str,
        *,
        new_game: bool = False,
        custom_word: str | None = None,
    ) -> Game:
        mode = self._resolve_mode(mode)
        db_session = self.db.session

        if mode == "daily":
            daily_word = self._get_or_create_daily_word()
            existing = db_session.execute(
                select(Game)
                .where(
                    Game.user_id == user.id,
                    Game.mode == "daily",
                    Game.daily_word_id == daily_word.id,
                )
                .order_by(Game.id.desc())
            ).scalars().first()
            if existing is not None:
                return existing
            game = Game(
                user_id=user.id,
                daily_word_id=daily_word.id,
                mode="daily",
                status="active",
                secret_word=daily_word.word,
                normalized_secret=daily_word.normalized_word,
            )
            db_session.add(game)
            db_session.commit()
            return game

        active = db_session.execute(
            select(Game)
            .where(
                Game.user_id == user.id,
                Game.mode == mode,
                Game.status == "active",
            )
            .order_by(Game.id.desc())
        ).scalars().first()

        if active is not None and not new_game:
            return active

        if active is not None and new_game:
            active.status = "abandoned"
            active.ended_at = utcnow()
            active = None

        if mode == "custom":
            latest_custom = db_session.execute(
                select(Game)
                .where(Game.user_id == user.id, Game.mode == "custom")
                .order_by(Game.id.desc())
            ).scalars().first()
            if not self.config["ALLOW_CUSTOM_MODE"]:
                raise ValueError("Le mode custom est désactivé dans cette configuration.")
            if custom_word:
                secret_word = self.semantic.validate_custom_secret(custom_word)
                if secret_word is None:
                    raise ValueError("Le mot custom doit appartenir au vocabulaire français autorisé.")
            elif latest_custom is not None and not new_game:
                return latest_custom
            elif active is None:
                raise ValueError("Le mode custom nécessite un mot secret valide.")
            else:
                return active
        else:
            secret_word = self.semantic.choose_random_secret()

        game = Game(
            user_id=user.id,
            mode=mode,
            status="active",
            secret_word=secret_word,
            normalized_secret=normalize_word(secret_word),
        )
        db_session.add(game)
        db_session.commit()
        return game

    def serialize_user(self, user: User) -> dict[str, Any]:
        return {
            "public_id": user.public_id,
            "display_name": user.display_name,
        }

    def serialize_game(self, game: Game) -> dict[str, Any]:
        guesses = sorted(game.guesses, key=lambda guess: (-guess.score, guess.attempt_number))
        secret_mask = game.secret_word if game.won else self.semantic.mask_secret(game.secret_word)
        return {
            "id": game.id,
            "mode": game.mode,
            "status": game.status,
            "won": game.won,
            "secret_mask": secret_mask,
            "secret_word": game.secret_word if game.won else None,
            "guess_count": game.attempts_count,
            "best_score": game.best_score,
            "hints_used": game.hints_used,
            "daily_date": game.daily_word.play_date.isoformat() if game.daily_word else None,
            "started_at": game.started_at.isoformat(),
            "ended_at": game.ended_at.isoformat() if game.ended_at else None,
            "guesses": [self.serialize_guess(guess) for guess in guesses],
            "hints": [self.serialize_hint(hint) for hint in game.hints],
            "available_hints": int(self.config["MAX_HINTS"]),
            "share_line": self.build_share_line(game),
        }

    def serialize_guess(self, guess: Guess) -> dict[str, Any]:
        return {
            "attempt_number": guess.attempt_number,
            "word": guess.word,
            "score": guess.score,
            "percentile": round(guess.percentile, 2),
            "semantic_rank": guess.semantic_rank,
            "temperature": guess.temperature,
            "exact": guess.is_exact,
            "created_at": guess.created_at.isoformat(),
        }

    def serialize_hint(self, hint: Hint) -> dict[str, Any]:
        return {
            "level": hint.level,
            "type": hint.hint_type,
            "content": hint.content,
            "created_at": hint.created_at.isoformat(),
        }

    def serialize_stats(self, user: User) -> dict[str, Any]:
        db_session = self.db.session
        total_games = db_session.scalar(select(func.count(Game.id)).where(Game.user_id == user.id)) or 0
        total_wins = db_session.scalar(
            select(func.count(Game.id)).where(Game.user_id == user.id, Game.won.is_(True))
        ) or 0
        best_score = db_session.scalar(
            select(func.max(Game.best_score)).where(Game.user_id == user.id)
        ) or 0
        average_attempts = db_session.scalar(
            select(func.avg(Game.attempts_count)).where(Game.user_id == user.id, Game.won.is_(True))
        ) or 0
        total_hints = db_session.scalar(
            select(func.coalesce(func.sum(Game.hints_used), 0)).where(Game.user_id == user.id)
        ) or 0

        per_mode: dict[str, dict[str, Any]] = {}
        for mode in ("daily", "infinite", "custom"):
            if mode == "custom" and not self.config["ALLOW_CUSTOM_MODE"]:
                continue
            played = db_session.scalar(
                select(func.count(Game.id)).where(Game.user_id == user.id, Game.mode == mode)
            ) or 0
            won = db_session.scalar(
                select(func.count(Game.id)).where(
                    Game.user_id == user.id,
                    Game.mode == mode,
                    Game.won.is_(True),
                )
            ) or 0
            per_mode[mode] = {
                "played": played,
                "won": won,
                "win_rate": round((won / played) * 100, 1) if played else 0.0,
            }

        return {
            "played": total_games,
            "won": total_wins,
            "best_score": best_score,
            "average_attempts_on_win": round(float(average_attempts), 1) if average_attempts else 0.0,
            "total_hints_used": int(total_hints),
            "win_rate": round((total_wins / total_games) * 100, 1) if total_games else 0.0,
            "per_mode": per_mode,
        }

    def serialize_leaderboard(self, mode: str, on_date: date | None = None) -> dict[str, Any]:
        mode = self._resolve_mode(mode)
        scope_date = on_date or date.today()
        scope_key = self._scope_key(mode, scope_date)
        query: Select[tuple[LeaderboardEntry]] = (
            select(LeaderboardEntry)
            .where(LeaderboardEntry.mode == mode, LeaderboardEntry.scope_key == scope_key)
            .order_by(
                LeaderboardEntry.attempts_count.asc(),
                LeaderboardEntry.hints_used.asc(),
                LeaderboardEntry.duration_seconds.asc(),
                LeaderboardEntry.rank_points.desc(),
                LeaderboardEntry.created_at.asc(),
            )
            .limit(int(self.config["LEADERBOARD_LIMIT"]))
        )
        entries = self.db.session.execute(query).scalars().all()
        return {
            "mode": mode,
            "scope_key": scope_key,
            "date": scope_date.isoformat() if mode == "daily" else None,
            "entries": [
                {
                    "position": index + 1,
                    "display_name": entry.display_name_snapshot,
                    "attempts_count": entry.attempts_count,
                    "hints_used": entry.hints_used,
                    "duration_seconds": entry.duration_seconds,
                    "best_score": entry.best_score,
                    "created_at": entry.created_at.isoformat(),
                }
                for index, entry in enumerate(entries)
            ],
        }

    def build_share_line(self, game: Game) -> str:
        label = {"daily": "daily", "infinite": "infinite", "custom": "custom"}[game.mode]
        if game.won:
            return f"Cemantix+ {label}: trouvé en {game.attempts_count} essais, {game.hints_used} indice(s)."
        return f"Cemantix+ {label}: {game.attempts_count} essais, meilleur score {game.best_score}."

    def _get_or_create_daily_word(self, target_date: date | None = None) -> DailyWord:
        target_date = target_date or date.today()
        db_session = self.db.session
        daily_word = db_session.execute(
            select(DailyWord).where(DailyWord.play_date == target_date)
        ).scalar_one_or_none()
        if daily_word is not None:
            return daily_word

        secret_word = self.semantic.choose_daily_secret(target_date)
        lexicon_entry = self.lexicon.get(secret_word)
        daily_word = DailyWord(
            play_date=target_date,
            word=secret_word,
            normalized_word=normalize_word(secret_word),
            source=self.semantic.engine_name,
            frequency_rank=lexicon_entry.rank,
        )
        db_session.add(daily_word)
        db_session.commit()
        return daily_word

    def _upsert_leaderboard_entry(self, game: Game) -> None:
        if not game.won:
            return
        db_session = self.db.session
        duration_seconds = max(1, int((game.ended_at - game.started_at).total_seconds())) if game.ended_at else 1
        existing = db_session.execute(
            select(LeaderboardEntry).where(LeaderboardEntry.game_id == game.id)
        ).scalar_one_or_none()
        user = game.user
        scope_key = self._scope_key(game.mode, self._leaderboard_date(game))
        rank_points = max(
            1,
            100_000 - (game.attempts_count * 140) - (game.hints_used * 35) - duration_seconds,
        )

        if existing is None:
            existing = LeaderboardEntry(
                user_id=user.id,
                game_id=game.id,
                display_name_snapshot=user.display_name,
                mode=game.mode,
                scope_key=scope_key,
                play_date=self._leaderboard_date(game),
                attempts_count=game.attempts_count,
                hints_used=game.hints_used,
                duration_seconds=duration_seconds,
                best_score=game.best_score,
                rank_points=rank_points,
            )
            db_session.add(existing)
            return

        existing.display_name_snapshot = user.display_name
        existing.scope_key = scope_key
        existing.play_date = self._leaderboard_date(game)
        existing.attempts_count = game.attempts_count
        existing.hints_used = game.hints_used
        existing.duration_seconds = duration_seconds
        existing.best_score = game.best_score
        existing.rank_points = rank_points

    def _leaderboard_date(self, game: Game | None) -> date:
        if game is not None and game.daily_word is not None:
            return game.daily_word.play_date
        return date.today()

    def _scope_key(self, mode: str, scope_date: date | None) -> str:
        if mode == "daily":
            return f"daily:{(scope_date or date.today()).isoformat()}"
        return f"{mode}:all"

    def _resolve_mode(self, mode: str | None) -> str:
        candidate = (mode or "daily").strip().lower()
        if candidate not in SUPPORTED_MODES:
            return "daily"
        if candidate == "custom" and not self.config["ALLOW_CUSTOM_MODE"]:
            return "daily"
        return candidate
