from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from kick_app.models import Announcement, UserRole  # Import UserRole

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/index")
@login_required
def index():
    """
    Main dashboard page.
    This now renders the dashboard template.
    """

    # --- ADD THIS LOGIC ---
    # Fetch all active announcements, newest first
    announcements = (
        Announcement.query.filter_by(is_active=True)
        .order_by(Announcement.created_at.desc())
        .all()
    )
    # --- END OF ADDITION ---
    # --- THIS IS THE CHANGE ---
    # We no longer redirect. We render the dashboard,
    # and the template itself will decide what to show.
    return render_template(
        "dashboard.html", title="Dashboard", announcements=announcements
    )
    # --- END OF CHANGE ---


@main.route("/profile")
@login_required
def profile():
    # ... (this route is unchanged)
    return render_template("profile.html", title="My Profile", user=current_user)
