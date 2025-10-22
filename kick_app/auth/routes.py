from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from . import auth
from .forms import LoginForm, RegistrationForm
from kick_app.models import User, UserRole
from kick_app import db


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

    return render_template("login.html", title="Sign In", form=form)


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
                return render_template("register.html", title="Register", form=form)

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

    return render_template("register.html", title="Register", form=form)
