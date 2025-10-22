from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from kick_app.models import UserRole  # Import UserRole

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/index")
@login_required
def index():
    """
    Main dashboard page.
    Redirects user to their specific dashboard.
    """
    if current_user.role == UserRole.ADMIN:
        # Admin sees the "All Tickets" page
        return redirect(url_for("tickets.all_tickets"))
    elif current_user.role == UserRole.TSR:
        # TSR sees "My Tickets"
        return redirect(url_for("tickets.my_tickets"))

    # Fallback (shouldn't be reached)
    return render_template("index.html", title="Dashboard")


@main.route("/profile")
@login_required
def profile():
    # ... (this route is unchanged)
    return render_template("profile.html", title="My Profile", user=current_user)
