from flask import render_template, request, flash
from flask_login import login_required
from . import rebate_bp
from .forms import RebateCalculatorForm
from .utils import calculate_rebate, format_duration  # Import helper functions
from ..models import Client
import pytz


@rebate_bp.route("/", methods=["GET", "POST"])
@login_required
def calculator():
    form = RebateCalculatorForm()
    result = None
    error = None

    # Pre-fill from URL
    account_num_from_url = request.args.get("account_number")
    if request.method == "GET" and account_num_from_url:
        form.account_number.data = account_num_from_url

    if form.validate_on_submit():
        account_number = form.account_number.data

        # 1. Get naive datetimes from form
        start_time_naive = form.start_time.data
        end_time_naive = form.end_time.data

        # 2. Make datetimes timezone-aware (PHT)
        pht_tz = pytz.timezone("Asia/Manila")
        start_time_aware = pht_tz.localize(start_time_naive)
        end_time_aware = pht_tz.localize(end_time_naive)

        # 3. Find Client in DB
        client = Client.query.filter_by(account_number=account_number).first()

        if not client:
            error = f"Account number '{account_number}' not found."
        elif client.plan_rate is None or client.plan_rate <= 0:
            error = f"Client '{client.account_name}' has no plan rate set (or is 0)."
        else:
            # 4. Check logic validity
            duration_seconds = (end_time_aware - start_time_aware).total_seconds()
            if duration_seconds < 0:
                error = "End time cannot be earlier than start time."
            else:
                # 5. Perform Calculation using new logic
                calc_data = calculate_rebate(
                    client.plan_rate, start_time_aware, end_time_aware
                )

                # 6. Prepare data for template
                result = {
                    "account_name": client.account_name,
                    "plan_rate": f"{client.plan_rate:,.2f}",
                    "downtime_duration": format_duration(duration_seconds),
                    # New Breakdown Data
                    "daily_rate": f"{calc_data['daily_rate']:,.3f}",
                    "hourly_rate": f"{calc_data['hourly_rate']:,.3f}",
                    "full_days_count": calc_data["full_days"],
                    "full_days_list": ", ".join(calc_data["full_days_list"]),
                    "partial_start_hours": f"{calc_data['partial_start_hours']:.3f}",
                    "partial_end_hours": f"{calc_data['partial_end_hours']:.3f}",
                    "rebate_start": f"{calc_data['rebate_partial_start']:,.2f}",
                    "rebate_full": f"{calc_data['rebate_full_days']:,.2f}",
                    "rebate_end": f"{calc_data['rebate_partial_end']:,.2f}",
                    "total_exact": f"{calc_data['total_rebate']:,.3f}",
                    "total_rounded": calc_data["total_rebate_rounded"],
                }

    return render_template(
        "calculator.html",
        title="Rebate Calculator",
        form=form,
        result=result,
        error=error,
    )
