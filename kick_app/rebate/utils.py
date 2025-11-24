from datetime import datetime, timedelta
import math


def format_duration(duration_seconds):
    """Converts seconds into a readable h/m/s format for display."""
    if duration_seconds < 0:
        return "0h 0m 0s (Invalid Date Range)"
    hours, remainder = divmod(duration_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


def calculate_rebate(monthly_rate, downtime_start, downtime_end, month_length=30):
    """
    Calculate service rebate based on downtime duration using specific
    rounding rules (3 decimal places for rates/hours, truncate final total).
    Returns a list of full days for transparency.
    """
    # Ensure correct order
    if downtime_end < downtime_start:
        downtime_start, downtime_end = downtime_end, downtime_start

    # 1. Calculate Rates (Rounded to 3 decimal places)
    daily_rate_raw = monthly_rate / month_length
    daily_rate = round(daily_rate_raw, 3)

    hourly_rate_raw = daily_rate / 24
    hourly_rate = round(hourly_rate_raw, 3)

    # If same-day downtime
    if downtime_start.date() == downtime_end.date():
        duration_seconds = (downtime_end - downtime_start).total_seconds()
        hours_raw = duration_seconds / 3600
        hours = round(hours_raw, 3)

        total_rebate = hours * hourly_rate

        return {
            "daily_rate": daily_rate,
            "hourly_rate": hourly_rate,
            "full_days": 0,
            "full_days_list": [],  # No full days
            "partial_start_hours": hours,
            "partial_end_hours": 0,
            "rebate_partial_start": round(total_rebate, 2),
            "rebate_full_days": 0,
            "rebate_partial_end": 0,
            "total_rebate": round(total_rebate, 2),
            "total_rebate_rounded": int(total_rebate),
        }

    # 2. Calculate Partial Start Day Hours
    # FIX: Apply the timezone from the input to the calculated midnight
    end_of_start_day = datetime.combine(downtime_start.date(), datetime.max.time())
    end_of_start_day = end_of_start_day.replace(tzinfo=downtime_start.tzinfo)

    # Add 1 microsecond to make it effectively the next midnight
    end_of_start_day = end_of_start_day + timedelta(microseconds=1)

    seconds_start = (end_of_start_day - downtime_start).total_seconds()
    hours_start_day_raw = seconds_start / 3600
    hours_start_day = round(hours_start_day_raw, 3)

    # 3. Calculate Partial End Day Hours
    # FIX: Apply the timezone from the input to the calculated morning
    start_of_end_day = datetime.combine(downtime_end.date(), datetime.min.time())
    start_of_end_day = start_of_end_day.replace(tzinfo=downtime_end.tzinfo)

    seconds_end = (downtime_end - start_of_end_day).total_seconds()
    hours_end_day_raw = seconds_end / 3600
    hours_end_day = round(hours_end_day_raw, 3)

    # 4. Calculate Full Days in between (Base count)
    full_days_count = (downtime_end.date() - downtime_start.date()).days - 1
    if full_days_count < 0:
        full_days_count = 0

    # --- ⭐️ NEW: Generate List of Middle Full Days ---
    full_days_list = []
    curr = downtime_start.date() + timedelta(days=1)
    while curr < downtime_end.date():
        full_days_list.append(curr.strftime("%b %d"))
        curr += timedelta(days=1)

    # 5. Normalize Logic (If a partial day is essentially 24 hours)
    if hours_start_day >= 24.0:
        hours_start_day = 0.0
        full_days_count += 1
        # Prepend start date to list
        full_days_list.insert(0, downtime_start.date().strftime("%b %d"))

    if hours_end_day >= 24.0:
        hours_end_day = 0.0
        full_days_count += 1
        # Append end date to list
        full_days_list.append(downtime_end.date().strftime("%b %d"))

    # 6. Calculate Final Rebate Components
    rebate_full_days = full_days_count * daily_rate
    rebate_start = hours_start_day * hourly_rate
    rebate_end = hours_end_day * hourly_rate

    total_rebate = rebate_full_days + rebate_start + rebate_end

    return {
        "daily_rate": daily_rate,
        "hourly_rate": hourly_rate,
        "full_days": full_days_count,
        "full_days_list": full_days_list,  # List of date strings
        "partial_start_hours": hours_start_day,
        "partial_end_hours": hours_end_day,
        "rebate_partial_start": round(rebate_start, 2),
        "rebate_full_days": round(rebate_full_days, 2),
        "rebate_partial_end": round(rebate_end, 2),
        "total_rebate": round(total_rebate, 3),
        "total_rebate_rounded": int(total_rebate),
    }
