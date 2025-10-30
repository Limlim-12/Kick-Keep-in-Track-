from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SubmitField, SelectField, TextAreaField, FloatField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField
from kick_app.models import Region


def get_regions():
    """Helper function to query all regions for the form."""
    return Region.query.all()


class ClientForm(FlaskForm):
    """Form for adding or editing a client."""

    account_number = StringField(
        "Account Number", validators=[DataRequired(), Length(max=100)]
    )
    account_name = StringField(
        "Account Name", validators=[DataRequired(), Length(max=200)]
    )

    plan_rate = FloatField(
        "Plan Rate (PHP)",
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Must be a positive number."),
        ],
    )
    
    region = QuerySelectField(
        "Region",
        query_factory=get_regions,
        get_label="name",
        allow_blank=False,
        validators=[DataRequired()],
    )
    status = SelectField(
        "Status",
        choices=[("Active", "Active"), ("Inactive", "Inactive")],
        default="Active",
    )
    submit = SubmitField("Save Client")


class ExcelUploadForm(FlaskForm):
    """Form for uploading an Excel file of clients."""

    excel_file = FileField(
        "Client Excel File",
        validators=[FileRequired(), FileAllowed(["xlsx", "xls"], "Excel files only!")],
    )
    submit = SubmitField("Upload")


class AnnouncementForm(FlaskForm):
    """Form for admins to create a new announcement."""

    message = TextAreaField(
        "Announcement Message", validators=[DataRequired(), Length(min=5, max=1000)]
    )
    submit = SubmitField("Post Announcement")


class ReportForm(FlaskForm):
    """Form for generating reports."""

    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])
    submit_tickets = SubmitField("Generate Ticket Report")
    # --- ADD THIS LINE ---
    submit_tsr = SubmitField("Generate TSR Performance Report")
