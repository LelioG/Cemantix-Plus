from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .utils.dates import utcnow


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(40), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    games: Mapped[list["Game"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries: Mapped[list["LeaderboardEntry"]] = relationship(back_populates="user")


class DailyWord(Base):
    __tablename__ = "daily_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    play_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    word: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_word: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), default="generated", nullable=False)
    frequency_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    games: Mapped[list["Game"]] = relationship(back_populates="daily_word")


class Game(TimestampMixin, Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    daily_word_id: Mapped[int | None] = mapped_column(ForeignKey("daily_words.id"), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    secret_word: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_secret: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_played_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="games")
    daily_word: Mapped["DailyWord | None"] = relationship(back_populates="games")
    guesses: Mapped[list["Guess"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="Guess.attempt_number",
    )
    hints: Mapped[list["Hint"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="Hint.level",
    )
    leaderboard_entry: Mapped["LeaderboardEntry | None"] = relationship(back_populates="game", uselist=False)


class Guess(Base):
    __tablename__ = "guesses"
    __table_args__ = (UniqueConstraint("game_id", "normalized_word", name="uq_guess_game_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    word: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_word: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    percentile: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature: Mapped[str] = mapped_column(String(20), nullable=False)
    is_exact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    game: Mapped["Game"] = relationship(back_populates="guesses")


class Hint(Base):
    __tablename__ = "hints"
    __table_args__ = (UniqueConstraint("game_id", "level", name="uq_hint_game_level"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    hint_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    game: Mapped["Game"] = relationship(back_populates="hints")


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"
    __table_args__ = (UniqueConstraint("game_id", name="uq_leaderboard_game"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    display_name_snapshot: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    play_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    best_score: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_points: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="leaderboard_entries")
    game: Mapped["Game"] = relationship(back_populates="leaderboard_entry")
