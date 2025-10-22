from flask import Blueprint

# Define the admin blueprint
admin = Blueprint(
    "admin", __name__, template_folder="../templates/admin", url_prefix="/admin"
)  # All routes will start with /admin

# Import the routes to register them with the blueprint
from . import routes
