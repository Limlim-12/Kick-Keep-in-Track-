from flask import render_template, request, flash
from flask_login import login_required
from . import rebate_bp  # Import our blueprint
from .forms import RebateCalculatorForm  # Import our new form
from .utils import calculate_rebate  # Import our new calculation logic
from ..models import Client  # Import Client to check account number
import pytz  # Import pytz for timezone handling


@rebate_bp.route("/", methods=["GET", "POST"])
@login_required
def calculator():
    form = RebateCalculatorForm()
    result = None
    error = None

    # This will pre-fill the form if a link from a ticket page is clicked
    account_num_from_url = request.args.get("account_number")
    if request.method == "GET" and account_num_from_url:
        form.account_number.data = account_num_from_url

    if form.validate_on_submit():
        account_number = form.account_number.data

        # 1. Get naive datetimes from form (assumed to be PHT)
        start_time_naive = form.start_time.data
        end_time_naive = form.end_time.data

        # 2. Make datetimes timezone-aware
        pht_tz = pytz.timezone("Asia/Manila")
        start_time_aware = pht_tz.localize(start_time_naive)
        end_time_aware = pht_tz.localize(end_time_naive)

        # 3. Pass aware datetimes to the calculation function
        subscriber_info, formatted_duration, rebate_amount, downtime_seconds = (
            calculate_rebate(account_number, start_time_aware, end_time_aware)
        )

        if subscriber_info is None:
            # If calculate_rebate returns None, it means an error occurred
            error = formatted_duration  # The error message is in this variable
        else:
            # If successful, format the results for display
            result = {
                "account_name": subscriber_info.get("name"),
                "plan_rate": f"{subscriber_info.get('plan_rate'):.2f}",
                "downtime_duration": formatted_duration,
                "rebate_amount": f"{rebate_amount:.2f}",
            }

    elif request.method == "POST":
        # If form validation fails, flash the errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")

    # This will render calculator.html, which we will create in the next part
    return render_template(
        "calculator.html",
        title="Rebate Calculator",
        form=form,
        result=result,
        error=error,
    )
