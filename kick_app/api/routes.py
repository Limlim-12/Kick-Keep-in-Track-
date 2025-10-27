from flask import jsonify, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from . import api
from kick_app import db
from kick_app.models import (
    Ticket,
    User,
    TicketStatus,
    UserRole,
    Announcement,
    Client,
    Region,
    ActivityLog,
)  #
from kick_app.__init__ import format_datetime_pht  #
from sqlalchemy import func
from datetime import datetime, date, timedelta
import io
import pandas as pd  # Ensure pandas is imported


# --- HELPER FOR DATES ---
def get_start_end_dates(start_str, end_str):
    """Parses date strings and returns datetime objects for start and end."""
    try:
        # Default to today if dates are missing or invalid
        start_date = (
            datetime.strptime(start_str, "%Y-%m-%d")
            if start_str
            else datetime.combine(date.today(), datetime.min.time())
        )
        end_date_obj = (
            datetime.strptime(end_str, "%Y-%m-%d") if end_str else date.today()
        )
        # Ensure end_date includes the entire day
        end_date = datetime.combine(end_date_obj, datetime.max.time())
    except (ValueError, TypeError):
        # Fallback nicely if parsing fails
        start_date = datetime.combine(date.today(), datetime.min.time())
        end_date = datetime.combine(date.today(), datetime.max.time())
    # Ensure start_date is not after end_date
    if start_date > end_date:
        start_date = end_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )  # Make start = beginning of end date

    return start_date, end_date


# Removed get_today_range as it's replaced


@api.route("/dashboard-stats")
@login_required
def dashboard_stats():
    """
    Provides dashboard data based on role and optional date range.
    """
    # --- Get dates from request, use helper function ---
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    start_date, end_date = get_start_end_dates(
        start_date_str, end_date_str
    )  # Get parsed dates

    if current_user.role == UserRole.ADMIN:  #
        # --- Admin Stats ---

        # 1. Stat Cards
        # Filter "Created" and "Resolved" by the selected date range
        total_created_range = Ticket.query.filter(
            Ticket.created_at.between(start_date, end_date)  #
        ).count()

        resolved_range = Ticket.query.filter(
            Ticket.status == TicketStatus.RESOLVED,  #
            Ticket.updated_at.between(start_date, end_date),  #
        ).count()

        # Counts not dependent on date range (keep as 'all time')
        total_new = Ticket.query.filter(Ticket.status == TicketStatus.NEW).count()  #
        total_open = Ticket.query.filter(Ticket.status == TicketStatus.OPEN).count()  #
        total_inprogress = Ticket.query.filter(
            Ticket.status == TicketStatus.IN_PROGRESS  #
        ).count()
        total_pending = Ticket.query.filter(
            Ticket.status == TicketStatus.PENDING
        ).count()  #

        admin_stats = {
            "total_created": total_created_range,  # Renamed key
            "total_new": total_new,
            "total_open": total_open,
            "total_inprogress": total_inprogress,
            "total_pending": total_pending,
            "total_resolved": resolved_range,  # Use range count
        }

        # 2. Pie Chart (All Time - typically not filtered by date)
        status_query = (
            db.session.query(Ticket.status, func.count(Ticket.id))  #
            .group_by(Ticket.status)  #
            .all()
        )
        pie_data = {
            "labels": [status.value for status, count in status_query],  #
            "data": [count for status, count in status_query],
        }

        # 3. Bar Chart (Open/In-Progress - typically not filtered by date)
        tsr_query = (
            db.session.query(User.full_name, func.count(Ticket.id))  #
            .join(Ticket, User.id == Ticket.assigned_to_id)  #
            .filter(
                User.role == UserRole.TSR,  #
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),  #
            )
            .group_by(User.full_name)  #
            .order_by(func.count(Ticket.id).desc())
            .all()
        )
        bar_data = {
            "labels": [name for name, count in tsr_query],
            "data": [count for name, count in tsr_query],
        }

        return jsonify(
            role="admin", stats=admin_stats, pie_chart=pie_data, bar_chart=bar_data
        )

    else:
        # --- TSR Stats ---
        my_id = current_user.id

        # 1. Stat Cards
        # Use date range for Resolved count
        resolved_range = Ticket.query.filter(
            Ticket.assigned_to_id == my_id,
            Ticket.status == TicketStatus.RESOLVED,  #
            Ticket.updated_at.between(start_date, end_date),  #
        ).count()

        # Counts not dependent on date range (current snapshot)
        total_new = Ticket.query.filter(
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.NEW  #
        ).count()
        total_open = Ticket.query.filter(
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.OPEN  #
        ).count()
        total_inprogress = Ticket.query.filter(
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.IN_PROGRESS  #
        ).count()
        total_pending = Ticket.query.filter(
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.PENDING  #
        ).count()

        # Avg Resolution Time (remains 'all time' for TSR dashboard simplicity)
        resolved_tickets_all_time = Ticket.query.filter(  #
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.RESOLVED  #
        ).all()
        total_resolution_time_tsr = timedelta(0)
        resolved_count_tsr = len(resolved_tickets_all_time)
        avg_resolution_minutes_tsr = 0
        if resolved_count_tsr > 0:
            for ticket in resolved_tickets_all_time:
                resolution_time = ticket.updated_at - ticket.created_at  #
                total_resolution_time_tsr += resolution_time
            avg_resolution_seconds_tsr = (
                total_resolution_time_tsr.total_seconds() / resolved_count_tsr
            )
            avg_resolution_minutes_tsr = avg_resolution_seconds_tsr / 60

        tsr_stats = {
            "total_new": total_new,
            "total_open": total_open,
            "total_inprogress": total_inprogress,
            "total_pending": total_pending,
            "total_resolved": resolved_range,  # Use range count
            "avg_resolution_time": f"{avg_resolution_minutes_tsr:.2f}",
        }

        # --- UPDATE Line Chart to use date range ---
        labels = []
        data = []
        # Calculate number of days in the range
        delta = end_date.date() - start_date.date()
        num_days = delta.days + 1  # Include both start and end day

        for i in range(num_days):
            day = start_date.date() + timedelta(days=i)
            day_start_dt = datetime.combine(day, datetime.min.time())
            day_end_dt = datetime.combine(day, datetime.max.time())

            labels.append(day.strftime("%a, %b %d"))  # Format label

            count = Ticket.query.filter(
                Ticket.assigned_to_id == my_id,
                Ticket.status == TicketStatus.RESOLVED,  #
                Ticket.updated_at.between(day_start_dt, day_end_dt),  #
            ).count()
            data.append(count)

        line_data = {"labels": labels, "data": data}
        # --- END Line Chart Update ---

        return jsonify(
            role="tsr",
            stats=tsr_stats,
            line_chart=line_data,
        )


# --- Other API routes (export_tickets, export_tsr_performance) remain below ---
@api.route("/export/tickets")  #
@login_required
def export_tickets():
    """
    Handles the generation and download of the ticket report.
    """
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        flash("Date range is required for reports.", "danger")
        return redirect(url_for("admin.reports"))

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.combine(
        datetime.strptime(end_date_str, "%Y-%m-%d"), datetime.max.time()
    )

    tickets_query = (
        Ticket.query.filter(Ticket.created_at.between(start_date, end_date))  #
        .order_by(Ticket.created_at.asc())  #
        .all()
    )

    if not tickets_query:
        flash("No tickets found for the selected date range.", "warning")
        return redirect(url_for("admin.reports"))

    data = []
    for ticket in tickets_query:
        data.append(
            {
                "Ticket ID": ticket.id,  #
                "Ticket Name": ticket.ticket_name,  #
                "Concern Title": ticket.concern_title,  #
                "Status": ticket.status.value,  #
                "Created At (PHT)": format_datetime_pht(ticket.created_at),  #
                "Last Updated (PHT)": format_datetime_pht(ticket.updated_at),  #
                "Assigned TSR": (
                    ticket.assigned_tsr.full_name  #
                    if ticket.assigned_tsr  #
                    else "Unassigned"
                ),
                "Client Name": ticket.client.account_name,  #
                "Account Number": ticket.client.account_number,  #
                "Region": ticket.client.region.name,  #
                "Created By": ticket.creator.full_name if ticket.creator else "N/A",  #
            }
        )

    df = pd.DataFrame(data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Ticket_Report", index=False)

    output.seek(0)
    filename = f"Kick_Ticket_Report_{start_date_str}_to_{end_date_str}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@api.route("/export/tsr-performance")  #
@login_required
def export_tsr_performance():
    """
    Generates and downloads the TSR Performance Report.
    """
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        flash("Date range is required for reports.", "danger")
        return redirect(url_for("admin.reports"))

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    end_date = datetime.combine(end_date_dt, datetime.max.time())

    active_tsrs = (
        User.query.filter(User.role == UserRole.TSR, User.is_active == True)  #
        .order_by(User.full_name)  #
        .all()
    )

    if not active_tsrs:
        flash("No active TSRs found to generate a report for.", "warning")
        return redirect(url_for("admin.reports"))

    report_data = []
    for tsr in active_tsrs:
        assigned_count = Ticket.query.filter(
            Ticket.assigned_to_id == tsr.id,  #
            Ticket.created_at.between(start_date, end_date),  #
        ).count()

        resolved_tickets = Ticket.query.filter(
            Ticket.assigned_to_id == tsr.id,  #
            Ticket.status == TicketStatus.RESOLVED,  #
            Ticket.updated_at.between(start_date, end_date),  #
        ).all()
        resolved_count = len(resolved_tickets)

        resolution_rate = (
            (resolved_count / assigned_count * 100) if assigned_count > 0 else 0
        )

        total_resolution_time = timedelta(0)
        if resolved_count > 0:
            for ticket in resolved_tickets:
                resolved_log = (
                    ActivityLog.query.filter(  #
                        ActivityLog.ticket_id == ticket.id,  #
                        ActivityLog.action.like("%Status changed% to Resolved%"),  #
                    )
                    .order_by(ActivityLog.timestamp.desc())  #
                    .first()
                )

                resolution_time = timedelta(0)
                if resolved_log:
                    resolution_time = resolved_log.timestamp - ticket.created_at  #
                else:
                    resolution_time = ticket.updated_at - ticket.created_at  #

                total_resolution_time += resolution_time

            avg_resolution_seconds = (
                total_resolution_time.total_seconds() / resolved_count
            )
            avg_resolution_minutes = avg_resolution_seconds / 60
        else:
            avg_resolution_minutes = 0

        report_data.append(
            {
                "TSR Name": tsr.full_name,  #
                "Tickets Assigned": assigned_count,
                "Tickets Resolved": resolved_count,
                "Resolution Rate (%)": f"{resolution_rate:.2f}%",
                "Avg Resolution Time (Minutes)": f"{avg_resolution_minutes:.2f}",
            }
        )

    if not report_data:
        flash(
            "No relevant ticket data found for active TSRs in the selected date range.",
            "warning",
        )
        return redirect(url_for("admin.reports"))

    df = pd.DataFrame(report_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="TSR_Performance", index=False)

    output.seek(0)
    filename = f"Kick_TSR_Performance_{start_date_str}_to_{end_date_str}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
