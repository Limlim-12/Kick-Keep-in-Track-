from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from .config import Config
from datetime import datetime  # <-- IMPORT DATETIME
import pytz  # <-- IMPORT PYTZ

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

# Set the view function name for the login page
# Flask-Login will redirect users to this route if they try to access a protected page
login_manager.login_view = "auth.login"  # We will create an 'auth' blueprint later
login_manager.login_message_category = "info"  # For flashing messages


# --- NEW TIMEZONE FILTER ---
def format_datetime_pht(utc_dt):
    """Converts a UTC datetime object to PHT (Philippines) string."""
    if not utc_dt:
        return "N/A"
    pht_tz = pytz.timezone("Asia/Manila")
    pht_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(pht_tz)
    return pht_dt.strftime("%Y-%m-%d %H:%M")


# --- END OF FILTER ---


def create_app(config_class=Config):
    """
    Create and configure an instance of the Flask application.
    This is the "Application Factory" pattern.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- REGISTER THE FILTER ---
    app.jinja_env.filters["pht"] = format_datetime_pht

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate

    # --- Register Blueprints (Routes) ---
    # Blueprints help organize routes into modules

    # Import and register the auth blueprint
    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint, url_prefix="/auth")

    # Simple main routes
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Import and register the admin blueprint
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    # Import and register the tickets blueprint
    from .tickets import tickets as tickets_blueprint
    app.register_blueprint(tickets_blueprint)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint)

    # This 'with' block ensures that the app context is active
    # when we create the tables, which is necessary for SQLAlchemy.
    with app.app_context():
        # Import models here so that Flask-Migrate can detect them
        from . import models

        # You can use db.create_all() for initial setup
        # db.create_all()
        # But for changes, we will now use Flask-Migrate

    return app
