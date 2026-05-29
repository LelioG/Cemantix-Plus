from __future__ import annotations

from flask import Blueprint, current_app, render_template, request


web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return render_template(
        "index.html",
        app_title=current_app.config["APP_TITLE"],
        initial_mode=request.args.get("mode", "daily"),
    )


@web_bp.get("/leaderboard")
def leaderboard_page():
    return render_template(
        "index.html",
        app_title=current_app.config["APP_TITLE"],
        initial_mode=request.args.get("mode", "daily"),
    )
