from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields import DateTimeField
from wtforms.validators import DataRequired


class RebateCalculatorForm(FlaskForm):
    """Form for the rebate calculator inputs."""

    account_number = StringField("Account Number", validators=[DataRequired()])

    start_time = DateTimeField(
        "Downtime Start (PHT)", validators=[DataRequired()], format="%Y-%m-%dT%H:%M"
    )

    end_time = DateTimeField(
        "Downtime End (PHT)", validators=[DataRequired()], format="%Y-%m-%dT%H:%M"
    )

    submit = SubmitField("Calculate Rebate")
