import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess-this-secret"
    ADMIN_SECRET_KEY = (
        os.environ.get("ADMIN_SECRET_KEY") or "kick-admin-secret-2025"
    )  # Keep this for Render env var

    # --- UPDATED DATABASE CONFIG ---
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    else:
        # Fallback to SQLite for local development if DATABASE_URL isn't set
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.db")
    # --- END OF UPDATE ---

    SQLALCHEMY_TRACK_MODIFICATIONS = False
