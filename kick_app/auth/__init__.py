from flask import Blueprint

# Define the blueprint
auth = Blueprint("auth", __name__, template_folder="../templates/auth")

# Import the routes to register them with the blueprint
from . import routes
