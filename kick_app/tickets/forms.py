from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length
from wtforms_sqlalchemy.fields import QuerySelectField
from kick_app.models import Client, TicketStatus


def get_clients():
    """Helper function to query all clients, ordered by name."""
    return Client.query.order_by(Client.account_name).all()


class TicketForm(FlaskForm):
    """Form for Admins to create a new ticket."""

    client = QuerySelectField(
        "Client (Search by Account Name or #)",
        query_factory=get_clients,
        get_label=lambda c: f"{c.account_name} ({c.account_number})",
        allow_blank=False,
        validators=[DataRequired()],
    )

    # --- NEW FIELD ---
    concern_title = StringField(
        "Concern Title", validators=[DataRequired(), Length(min=1, max=100)]
    )

    # --- RENAMED FIELD ---
    concern_details = TextAreaField(
        "Concern Details", validators=[DataRequired(), Length(max=1000)]
    )

    submit = SubmitField("Create Ticket")


class UpdateTicketForm(FlaskForm):
    """Form for TSRs to update a ticket."""

    status = SelectField(
        "Update Status",
        choices=[(status.name, status.value) for status in TicketStatus],
        validators=[DataRequired()],
    )
    remarks = TextAreaField(
        "Add Remarks/Notes", validators=[DataRequired(), Length(min=5, max=1000)]
    )
    submit = SubmitField("Update Ticket")
