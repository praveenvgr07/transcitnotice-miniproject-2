"""Main routes – homepage and static pages."""
from flask import Blueprint, render_template, request
from models.schedule_model import get_latest_announcements, get_all_sources

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    announcements = get_latest_announcements(limit=6)
    sources       = get_all_sources()
    return render_template("index.html", announcements=announcements, sources=sources)


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@main_bp.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500
