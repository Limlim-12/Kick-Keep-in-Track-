from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from kick_app.models import User


class LoginForm(FlaskForm):
    """Form for user login."""

    # Updated to use Employee ID
    employee_id = StringField("Employee ID", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    """Form for new user registration."""

    # Updated and new fields
    employee_id = StringField(
        "Employee ID", validators=[DataRequired(), Length(min=3, max=80)]
    )
    full_name = StringField(
        "Full Name", validators=[DataRequired(), Length(min=3, max=150)]
    )
    email = StringField("Company Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )

    # New field for Admin secret
    secret_key = PasswordField("Admin Secret Key (leave blank for TSR)")

    submit = SubmitField("Register")

    def validate_employee_id(self, employee_id):
        """Check if employee ID already exists."""
        user = User.query.filter_by(employee_id=employee_id.data).first()
        if user:
            raise ValidationError("That Employee ID is. already registered.")

    def validate_email(self, email):
        """Check if email already exists."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("That email is already in use.")


# --- NEW: Password Reset Request Form ---
class RequestResetForm(FlaskForm):
    """Form for user to request a password reset email."""

    email = StringField("Company Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")

    def validate_email(self, email):
        """Check if email exists in the database."""
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError(
                "There is no account with that email. You must register first."
            )


# --- NEW: Password Reset Form ---
class ResetPasswordForm(FlaskForm):
    """Form for user to set a new password."""

    password = PasswordField("New Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Reset Password")
