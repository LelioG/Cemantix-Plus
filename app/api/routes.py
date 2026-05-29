from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, session


api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def game_service():
    return current_app.extensions["game_service"]


@api_bp.get("/bootstrap")
def bootstrap():
    payload = game_service().bootstrap(session, request.args.get("mode"))
    session.modified = True
    return jsonify(payload)


@api_bp.post("/game/select")
def select_game():
    payload = request.get_json(silent=True) or {}
    response = game_service().select_game(
        session,
        payload.get("mode", "daily"),
        new_game=bool(payload.get("new_game", False)),
        custom_word=payload.get("custom_word"),
    )
    session.modified = True
    status = 200 if response.get("ok") else 400
    return jsonify(response), status


@api_bp.post("/game/guess")
def guess():
    payload = request.get_json(silent=True) or {}
    response = game_service().process_guess(session, payload.get("word", ""))
    session.modified = True
    status = 200 if response.get("ok") else 400
    return jsonify(response), status


@api_bp.post("/game/hint")
def hint():
    response = game_service().request_hint(session)
    session.modified = True
    status = 200 if response.get("ok") else 400
    return jsonify(response), status


@api_bp.get("/leaderboard")
def leaderboard():
    raw_date = request.args.get("date")
    scope_date = None
    if raw_date:
        scope_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    response = game_service().get_leaderboard_payload(
        session,
        mode=request.args.get("mode"),
        on_date=scope_date,
    )
    session.modified = True
    return jsonify(response)


@api_bp.get("/stats")
def stats():
    response = game_service().get_stats_payload(session)
    session.modified = True
    return jsonify(response)


@api_bp.put("/profile")
def profile():
    payload = request.get_json(silent=True) or {}
    response = game_service().update_profile(session, payload.get("display_name", ""))
    session.modified = True
    status = 200 if response.get("ok") else 400
    return jsonify(response), status


@api_bp.get("/health")
def health():
    return jsonify(game_service().get_health())
