from datetime import datetime
from ..models import Client  # Import the Client model from KICK


def format_duration(duration_seconds):
    """Converts seconds into a readable h/m/s format."""
    if duration_seconds < 0:
        return "0h 0m 0s (Invalid Date Range)"

    hours, remainder = divmod(duration_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


def calculate_rebate(account_number, start_time, end_time):
    """
    Calculates the rebate amount based on data from the KICK database.
    Takes timezone-aware datetime objects as input.
    """

    # --- THIS IS THE FULL INTEGRATION ---
    # Find the client in the KICK database
    client = Client.query.filter_by(account_number=account_number).first()

    if not client:
        return (
            None,
            f"Account number '{account_number}' not found in KICK database.",
            0,
            0,
        )

    # We check the plan_rate we added in Part 1
    if client.plan_rate is None or client.plan_rate <= 0:
        return (
            None,
            f"Client '{client.account_name}' has no plan rate set. Please update this client in the Admin panel.",
            0,
            0,
        )

    subscriber_info = {"name": client.account_name, "plan_rate": client.plan_rate}
    plan_rate = client.plan_rate
    # --- END INTEGRATION ---

    # Calculate downtime duration in seconds
    downtime_duration = end_time - start_time
    downtime_seconds = downtime_duration.total_seconds()

    if downtime_seconds < 0:
        return (
            subscriber_info,
            "End time cannot be earlier than start time.",
            0,
            downtime_seconds,
        )

    # Constants for calculation (from your original rebate_calculator.py)
    days_in_month = 30
    seconds_in_day = 24 * 60 * 60
    threshold_seconds = 2 * 60 * 60  # 2 hours

    rebate_amount = 0
    if downtime_seconds > threshold_seconds:
        rebate_amount = (plan_rate / days_in_month / seconds_in_day) * downtime_seconds

    formatted_duration = format_duration(downtime_seconds)

    return subscriber_info, formatted_duration, rebate_amount, downtime_seconds
