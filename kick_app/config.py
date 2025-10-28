import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess-this-secret"
    ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY") or "20251022kickadmin"

    # --- REVISED DATABASE CONFIG ---
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    if SQLALCHEMY_DATABASE_URI:  # Check if the variable exists at all
        print(
            f"DATABASE_URL found: {SQLALCHEMY_DATABASE_URI[:20]}..."
        )  # Log confirmation
        # If it starts with postgres://, replace it with postgresql:// for SQLAlchemy compatibility
        if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
                "postgres://", "postgresql://", 1
            )
            print("Corrected DATABASE_URL prefix to postgresql://")
        # Ensure it starts correctly now
        if not SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
            print(
                f"WARNING: DATABASE_URL does not start with postgresql://. Current value: {SQLALCHEMY_DATABASE_URI}"
            )
            # You might add more specific error handling or fallbacks here if needed

    else:
        # ONLY fall back to SQLite if DATABASE_URL is completely missing
        print(
            "WARNING: DATABASE_URL not set, falling back to SQLite."
        )  # Add a warning for logs
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.db")
    # --- END OF REVISION ---

    SQLALCHEMY_TRACK_MODIFICATIONS = False
