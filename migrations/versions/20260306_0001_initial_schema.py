from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260306_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=40), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_public_id", "users", ["public_id"], unique=True)

    op.create_table(
        "daily_words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("play_date", sa.Date(), nullable=False),
        sa.Column("word", sa.String(length=80), nullable=False),
        sa.Column("normalized_word", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("frequency_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_daily_words_play_date", "daily_words", ["play_date"], unique=True)
    op.create_index("ix_daily_words_normalized_word", "daily_words", ["normalized_word"], unique=False)

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("daily_word_id", sa.Integer(), sa.ForeignKey("daily_words.id"), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("secret_word", sa.String(length=80), nullable=False),
        sa.Column("normalized_secret", sa.String(length=80), nullable=False),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("won", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("last_played_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_games_user_id", "games", ["user_id"], unique=False)
    op.create_index("ix_games_daily_word_id", "games", ["daily_word_id"], unique=False)
    op.create_index("ix_games_mode", "games", ["mode"], unique=False)
    op.create_index("ix_games_status", "games", ["status"], unique=False)
    op.create_index("ix_games_normalized_secret", "games", ["normalized_secret"], unique=False)

    op.create_table(
        "guesses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(length=80), nullable=False),
        sa.Column("normalized_word", sa.String(length=80), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=False),
        sa.Column("semantic_rank", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.String(length=20), nullable=False),
        sa.Column("is_exact", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("game_id", "normalized_word", name="uq_guess_game_word"),
    )
    op.create_index("ix_guesses_game_id", "guesses", ["game_id"], unique=False)
    op.create_index("ix_guesses_normalized_word", "guesses", ["normalized_word"], unique=False)

    op.create_table(
        "hints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("hint_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("game_id", "level", name="uq_hint_game_level"),
    )
    op.create_index("ix_hints_game_id", "hints", ["game_id"], unique=False)

    op.create_table(
        "leaderboard_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("display_name_snapshot", sa.String(length=40), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("scope_key", sa.String(length=60), nullable=False),
        sa.Column("play_date", sa.Date(), nullable=True),
        sa.Column("attempts_count", sa.Integer(), nullable=False),
        sa.Column("hints_used", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("best_score", sa.Integer(), nullable=False),
        sa.Column("rank_points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("game_id", name="uq_leaderboard_game"),
    )
    op.create_index("ix_leaderboard_entries_user_id", "leaderboard_entries", ["user_id"], unique=False)
    op.create_index("ix_leaderboard_entries_game_id", "leaderboard_entries", ["game_id"], unique=False)
    op.create_index("ix_leaderboard_entries_mode", "leaderboard_entries", ["mode"], unique=False)
    op.create_index("ix_leaderboard_entries_scope_key", "leaderboard_entries", ["scope_key"], unique=False)
    op.create_index("ix_leaderboard_entries_play_date", "leaderboard_entries", ["play_date"], unique=False)
    op.create_index("ix_leaderboard_entries_rank_points", "leaderboard_entries", ["rank_points"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_leaderboard_entries_rank_points", table_name="leaderboard_entries")
    op.drop_index("ix_leaderboard_entries_play_date", table_name="leaderboard_entries")
    op.drop_index("ix_leaderboard_entries_scope_key", table_name="leaderboard_entries")
    op.drop_index("ix_leaderboard_entries_mode", table_name="leaderboard_entries")
    op.drop_index("ix_leaderboard_entries_game_id", table_name="leaderboard_entries")
    op.drop_index("ix_leaderboard_entries_user_id", table_name="leaderboard_entries")
    op.drop_table("leaderboard_entries")

    op.drop_index("ix_hints_game_id", table_name="hints")
    op.drop_table("hints")

    op.drop_index("ix_guesses_normalized_word", table_name="guesses")
    op.drop_index("ix_guesses_game_id", table_name="guesses")
    op.drop_table("guesses")

    op.drop_index("ix_games_normalized_secret", table_name="games")
    op.drop_index("ix_games_status", table_name="games")
    op.drop_index("ix_games_mode", table_name="games")
    op.drop_index("ix_games_daily_word_id", table_name="games")
    op.drop_index("ix_games_user_id", table_name="games")
    op.drop_table("games")

    op.drop_index("ix_daily_words_normalized_word", table_name="daily_words")
    op.drop_index("ix_daily_words_play_date", table_name="daily_words")
    op.drop_table("daily_words")

    op.drop_index("ix_users_public_id", table_name="users")
    op.drop_table("users")
