import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Set Flask configuration variables from a class."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess-this-secret"

    # ADD THIS LINE
    ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY") or "20251022kickadmin"

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
