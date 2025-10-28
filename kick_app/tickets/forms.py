from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    TextAreaField,
    SelectField,
    BooleanField,
    DateTimeField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
)  # Ensure Optional is imported
from wtforms_sqlalchemy.fields import QuerySelectField
from kick_app.models import Client, TicketStatus, User, UserRole
from datetime import datetime


def get_clients():
    """Helper function to query all clients, ordered by name."""
    return Client.query.order_by(Client.account_name).all()


def get_tsrs():
    """Helper function to query all active TSRs."""
    return (
        User.query.filter(User.role == UserRole.TSR, User.is_active == True)
        .order_by(User.full_name)
        .all()
    )


class TicketForm(FlaskForm):
    """Form for Admins to create a new ticket."""

    client = QuerySelectField(
        "Client (Search by Account Name or #)",
        query_factory=get_clients,
        get_label=lambda c: f"{c.account_name} ({c.account_number})",
        allow_blank=False,
        validators=[DataRequired()],
    )

    concern_title = StringField(
        "Concern Title",
        validators=[DataRequired(), Length(max=100)],  # Removed min=1 for flexibility
    )

    concern_details = TextAreaField(
        "Concern Details", validators=[DataRequired(), Length(max=1000)]
    )

    submit = SubmitField("Create Ticket")


# --- CORRECTED UpdateTicketForm ---
class UpdateTicketForm(FlaskForm):
    """Form for TSRs/Admins to update a ticket."""

    status = SelectField(
        "Update Status",
        choices=[(status.name, status.value) for status in TicketStatus],
        validators=[DataRequired()],
    )

    # This field is for Admins to reassign
    assigned_tsr = QuerySelectField(
        "Assign/Reassign to TSR",
        query_factory=get_tsrs,
        get_label="full_name",
        allow_blank=True,  # Allows 'Unassigned' selection
        validators=[],  # Not strictly required for the update action
    )

    # Field for RT Ticket Number input
    rt_ticket_number = StringField(
        "RT Ticket Number", validators=[Optional(), Length(max=100)]
    )

    # --- ADD THIS FIELD ---
    email_sent = BooleanField("Mark as Email Sent/Replied")

    remarks = TextAreaField(
        "Add Remarks/Notes", validators=[Optional(), Length(min=5, max=1000)]
    )

    submit = SubmitField("Update Ticket")

    # Field for adding remarks
    remarks = TextAreaField(
        "Add Remarks/Notes",
        validators=[Optional(), Length(min=5, max=1000)],  # Kept Optional
    )

    submit = SubmitField("Update Ticket")


# --- END CORRECTION ---


# --- ADD THIS ENTIRE NEW FORM ---
class EmailLogForm(FlaskForm):
    """Form for logging an email sent to a client."""

    email_content = TextAreaField(
        "Paste Email Content Here",
        validators=[DataRequired(), Length(min=10)],
        render_kw={"rows": 10},
    )
    sent_at = DateTimeField(
        "Date and Time Sent (PHT)",
        validators=[DataRequired()],
        default=datetime.now,  # Defaults to current time
        format="%Y-%m-%dT%H:%M",  # Format for datetime-local input
    )
    submit_email_log = SubmitField("Log Email")


# --- END OF NEW FORM ---
