from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from .config import Config
from datetime import datetime
import pytz

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

# Set the view function name for the login page
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


# --- FILTERS ---


def format_datetime_pht(utc_dt):
    """Converts a UTC datetime object to PHT (Philippines) string."""
    if not utc_dt:
        return "N/A"
    pht_tz = pytz.timezone("Asia/Manila")
    pht_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(pht_tz)
    return pht_dt.strftime("%Y-%m-%d %H:%M")


def strip_timestamp_filter(ticket_name):
    """Removes the Unix timestamp suffix from the ticket name."""
    if not ticket_name:
        return ""
    return ticket_name.rsplit("_", 1)[0]


def sla_class_filter(created_at):
    """Returns a Bootstrap color class based on ticket age."""
    if not created_at:
        return "secondary"  # Gray default

    now = datetime.utcnow()
    diff = now - created_at
    hours = diff.total_seconds() / 3600

    if hours < 4:
        return "success"  # Green (Fresh)
    elif hours < 24:
        return "warning text-dark"  # Yellow (Aging)
    else:
        return "danger"  # Red (Overdue)


# --- APP FACTORY ---


def create_app(config_class=Config):
    """
    Create and configure an instance of the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- REGISTER FILTERS ---
    app.jinja_env.filters["pht"] = format_datetime_pht
    app.jinja_env.filters["no_stamp"] = strip_timestamp_filter
    app.jinja_env.filters["sla"] = sla_class_filter

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # --- Register Blueprints (Routes) ---
    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    from .routes import main as main_blueprint

    app.register_blueprint(main_blueprint)

    from .admin import admin as admin_blueprint

    app.register_blueprint(admin_blueprint)

    from .tickets import tickets as tickets_blueprint

    app.register_blueprint(tickets_blueprint)

    from .api import api as api_blueprint

    app.register_blueprint(api_blueprint)

    from .rebate import rebate_bp

    app.register_blueprint(rebate_bp)

    with app.app_context():
        from . import models

    return app  # <--- THIS LINE WAS LIKELY MISSING OR INDENTED WRONG
