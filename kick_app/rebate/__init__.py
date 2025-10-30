# kick_app/rebate/__init__.py
from flask import Blueprint

rebate_bp = Blueprint(
    "rebate",  # <-- This should be "rebate"
    __name__,
    template_folder="../templates/rebate",
    url_prefix="/rebate",
)

from . import routes
