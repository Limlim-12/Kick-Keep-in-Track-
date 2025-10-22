from flask import Blueprint

# Define the tickets blueprint
tickets = Blueprint(
    "tickets", __name__, template_folder="../templates/tickets", url_prefix="/tickets"
)  # All routes will start with /tickets

# Import the routes to register them with the blueprint
from . import routes
