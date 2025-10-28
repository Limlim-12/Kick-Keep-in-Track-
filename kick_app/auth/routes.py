from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from . import auth
from .forms import (
    LoginForm,
    RegistrationForm,
    RequestResetForm,
    ResetPasswordForm,
)  # <-- Import new forms
from kick_app.models import User, UserRole
from .. import db, mail  
from flask_mail import Message  # <-- Import Message


# --- NEW: Email Sending Function ---
def send_reset_email(user):
    """Generates a token and sends the password reset email."""
    token = user.get_reset_token()
    reset_url = url_for("auth.reset_token", token=token, _external=True)

    # Get the app's configured sender email
    sender_email = current_app.config.get("MAIL_DEFAULT_SENDER")
    if not sender_email:
        flash(
            "Email server is not configured. Password reset is unavailable.", "danger"
        )
        print("ERROR: MAIL_DEFAULT_SENDER is not set in config.")
        return

    msg = Message(
        "Password Reset Request - KICK Application",
        sender=sender_email,
        recipients=[user.email],
    )
    msg.html = render_template("auth/reset_email.html", user=user, reset_url=reset_url)

    try:
        mail.send(msg)
    except Exception as e:
        # Log the error for debugging
        print(f"Error sending email: {e}")
        flash(
            "Failed to send password reset email. Please try again later or contact an admin.",
            "danger",
        )


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        # Find user by new employee_id field
        user = User.query.filter_by(employee_id=form.employee_id.data).first()

        # Check if user exists and password is correct
        if user and user.check_password(form.password.data):

            # --- NEW APPROVAL CHECK ---
            if not user.is_active:
                flash("Your account is pending admin approval. Please wait.", "warning")
                return redirect(url_for("auth.login"))
            # --- END OF NEW CHECK ---

            login_user(user, remember=form.remember_me.data)
            flash("Login successful!", "success")

            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("main.index"))
        else:
            flash("Invalid Employee ID or password.", "danger")

    return render_template("auth/login.html", title="Sign In", form=form)


@auth.route("/logout")
def logout():
    # ... (this function is unchanged)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    """Handle new user registration with Admin/TSR logic."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():

        # --- NEW ADMIN/TSR REGISTRATION LOGIC ---
        user = User(
            employee_id=form.employee_id.data,
            full_name=form.full_name.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)

        secret_key_from_form = form.secret_key.data
        admin_secret = current_app.config["ADMIN_SECRET_KEY"]

        # Check if they are trying to register as an Admin
        if secret_key_from_form:
            if secret_key_from_form == admin_secret:
                user.role = UserRole.ADMIN
                user.is_active = True
                flash("Admin account successfully created and activated!", "success")
            else:
                # Invalid secret key
                flash("Invalid Admin Secret Key. Registration failed.", "danger")
                return render_template(
                    "auth/register.html", title="Register", form=form
                )

        # Else, they are registering as a TSR (default role)
        else:
            user.role = UserRole.TSR
            user.is_active = False  # Remains False until approved
            flash(
                "Registration successful! Your account is now pending admin approval.",
                "info",
            )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", title="Register", form=form)


# --- NEW: Password Reset Request Route ---
@auth.route("/request-reset", methods=["GET", "POST"])
def request_reset():
    """Handles the request for a password reset."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
            flash(
                "An email has been sent with instructions to reset your password.",
                "info",
            )
            return redirect(url_for("auth.login"))
        else:
            flash("Email not found.", "danger")

    return render_template("auth/request_reset.html", title="Reset Password", form=form)


# --- NEW: Password Reset Token Route ---
@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_token(token):
    """Handles the actual password reset using the token."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.verify_reset_token(token)
    if user is None:
        flash("That is an invalid or expired token.", "warning")
        return redirect(url_Examples("auth.request_reset"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been updated! You are now able to log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/reset_token.html", title="Reset Your Password", form=form
    )
