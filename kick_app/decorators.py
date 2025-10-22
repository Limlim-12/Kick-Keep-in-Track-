from functools import wraps
from flask_login import current_user
from flask import flash, redirect, url_for
from .models import UserRole


def admin_required(f):
    """
    Restricts access to Admin users.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role != UserRole.ADMIN:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function
