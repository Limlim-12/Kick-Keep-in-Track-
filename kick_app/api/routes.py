from flask import jsonify, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from . import api
from kick_app import db

# --- ADD 'Announcement' AND 'format_datetime_pht' ---
from kick_app.models import (
    Ticket,
    User,
    TicketStatus,
    UserRole,
    Announcement,
    Client,
    Region,
    ActivityLog,
)
from kick_app.__init__ import format_datetime_pht
from sqlalchemy import func

# --- ADD 'timedelta', 'io', 'pandas' ---
from datetime import datetime, date, timedelta
import io
import pandas as pd


def get_today_range():
    """Returns the start and end datetime for the current day in UTC."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    return today_start, today_end


@api.route("/dashboard-stats")
@login_required
def dashboard_stats():
    """
    Provides all the necessary data for the user's dashboard
    based on their role.
    """
    today_start, today_end = get_today_range()

    if current_user.role == UserRole.ADMIN:
        # --- Admin Stats ---

        # 1. Stat Cards
        total_today = Ticket.query.filter(
            Ticket.created_at.between(today_start, today_end)
        ).count()

        total_open = Ticket.query.filter(Ticket.status == TicketStatus.OPEN).count()

        total_inprogress = Ticket.query.filter(
            Ticket.status == TicketStatus.IN_PROGRESS
        ).count()

        resolved_today = Ticket.query.filter(
            Ticket.status == TicketStatus.RESOLVED,
            Ticket.updated_at.between(today_start, today_end),
        ).count()

        admin_stats = {
            "total_today": total_today,
            "total_open": total_open,
            "total_inprogress": total_inprogress,
            "total_resolved": resolved_today,
        }

        # 2. Pie Chart: Ticket Status Breakdown
        status_query = (
            db.session.query(Ticket.status, func.count(Ticket.id))
            .group_by(Ticket.status)
            .all()
        )

        pie_data = {
            "labels": [status.value for status, count in status_query],
            "data": [count for status, count in status_query],
        }

        # 3. Bar Chart: Tickets per TSR (Open)
        tsr_query = (
            db.session.query(User.full_name, func.count(Ticket.id))
            .join(Ticket, User.id == Ticket.assigned_to_id)
            .filter(
                User.role == UserRole.TSR,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
            )
            .group_by(User.full_name)
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
        today_start, today_end = get_today_range()  # Get today's range

        # 1. Stat Cards
        total_open = Ticket.query.filter(
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.OPEN
        ).count()

        total_inprogress = Ticket.query.filter(
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.IN_PROGRESS
        ).count()

        resolved_today = Ticket.query.filter(
            Ticket.assigned_to_id == my_id,
            Ticket.status == TicketStatus.RESOLVED,
            Ticket.updated_at.between(today_start, today_end),
        ).count()

        # --- Calculate Average Resolution Time (for TSR) ---
        resolved_tickets_all_time = Ticket.query.filter(
            Ticket.assigned_to_id == my_id, Ticket.status == TicketStatus.RESOLVED
        ).all()

        total_resolution_time_tsr = timedelta(0)
        resolved_count_tsr = len(resolved_tickets_all_time)
        avg_resolution_minutes_tsr = 0

        if resolved_count_tsr > 0:
            for ticket in resolved_tickets_all_time:
                resolution_time = ticket.updated_at - ticket.created_at
                total_resolution_time_tsr += resolution_time

            avg_resolution_seconds_tsr = (
                total_resolution_time_tsr.total_seconds() / resolved_count_tsr
            )
            avg_resolution_minutes_tsr = avg_resolution_seconds_tsr / 60

        tsr_stats = {
            "total_open": total_open,
            "total_inprogress": total_inprogress,
            "total_resolved": resolved_today,
            "avg_resolution_time": f"{avg_resolution_minutes_tsr:.2f}",
        }

        # --- START: THIS SECTION WAS MISSING OR MISPLACED ---
        # 2. Line Chart: Weekly Performance
        today = date.today()
        labels = []
        data = []
        for i in range(6, -1, -1):  # From 6 days ago to today
            day = today - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())

            labels.append(day.strftime("%a, %b %d"))  # e.g., "Thu, Oct 23"

            count = Ticket.query.filter(
                Ticket.assigned_to_id == my_id,
                Ticket.status == TicketStatus.RESOLVED,
                Ticket.updated_at.between(day_start, day_end),
            ).count()
            data.append(count)

        line_data = {"labels": labels, "data": data}
        # --- END: THIS SECTION WAS MISSING OR MISPLACED ---

        return jsonify(
            role="tsr",
            stats=tsr_stats,
            line_chart=line_data,  # Now 'line_data' is defined
        )

@api.route("/export/tickets")
@login_required
def export_tickets():
    """
    Handles the generation and download of the ticket report.
    """
    # Get the dates from the URL query parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        flash("Date range is required for reports.", "danger")
        return redirect(url_for("admin.reports"))

    # Convert date strings back to datetime objects
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    # Add time component to end_date to include the entire day
    end_date = datetime.combine(
        datetime.strptime(end_date_str, "%Y-%m-%d"), datetime.max.time()
    )

    # --- Query the Database ---
    tickets_query = (
        Ticket.query.filter(Ticket.created_at.between(start_date, end_date))
        .order_by(Ticket.created_at.asc())
        .all()
    )

    if not tickets_query:
        flash("No tickets found for the selected date range.", "warning")
        return redirect(url_for("admin.reports"))

    # --- Convert to Pandas DataFrame ---
    data = []
    for ticket in tickets_query:
        data.append(
            {
                "Ticket ID": ticket.id,
                "Ticket Name": ticket.ticket_name,
                "Concern Title": ticket.concern_title,
                "Status": ticket.status.value,
                "Created At (PHT)": format_datetime_pht(ticket.created_at),
                "Last Updated (PHT)": format_datetime_pht(ticket.updated_at),
                "Assigned TSR": (
                    ticket.assigned_tsr.full_name
                    if ticket.assigned_tsr
                    else "Unassigned"
                ),
                "Client Name": ticket.client.account_name,
                "Account Number": ticket.client.account_number,
                "Region": ticket.client.region.name,
                "Created By": ticket.creator.full_name if ticket.creator else "N/A",
            }
        )

    df = pd.DataFrame(data)

    # --- Create Excel File in Memory ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Ticket_Report", index=False)

    output.seek(0)  # Move cursor to the start of the in-memory file

    # --- Send the File to the User ---
    filename = f"Kick_Ticket_Report_{start_date_str}_to_{end_date_str}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@api.route("/export/tsr-performance")
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
    end_date = datetime.combine(
        end_date_dt, datetime.max.time()
    )  # Include full end day

    # --- Query Active TSRs ---
    active_tsrs = (
        User.query.filter(User.role == UserRole.TSR, User.is_active == True)
        .order_by(User.full_name)
        .all()
    )

    if not active_tsrs:
        flash("No active TSRs found to generate a report for.", "warning")
        return redirect(url_for("admin.reports"))

    # --- Calculate Stats for Each TSR ---
    report_data = []
    for tsr in active_tsrs:
        # 1. Tickets Assigned within the period
        assigned_count = Ticket.query.filter(
            Ticket.assigned_to_id == tsr.id,
            # We need to decide: Assigned *during* the period, or *ever* assigned?
            # Let's assume assigned *during* the period for now. This requires an assignment log.
            # Since we don't explicitly log assignment *time*, let's count tickets CREATED and assigned during period
            Ticket.created_at.between(start_date, end_date),
        ).count()

        # 2. Tickets Resolved within the period by this TSR
        resolved_tickets = Ticket.query.filter(
            Ticket.assigned_to_id == tsr.id,
            Ticket.status == TicketStatus.RESOLVED,
            Ticket.updated_at.between(start_date, end_date),
        ).all()
        resolved_count = len(resolved_tickets)

        # 3. Resolution Rate (%)
        resolution_rate = (
            (resolved_count / assigned_count * 100) if assigned_count > 0 else 0
        )

        # 4. Average Resolution Time (in minutes)
        total_resolution_time = timedelta(0)
        if resolved_count > 0:
            for ticket in resolved_tickets:
                # Find the 'Resolved' log entry for this ticket to get accurate time
                resolved_log = (
                    ActivityLog.query.filter(
                        ActivityLog.ticket_id == ticket.id,
                        ActivityLog.action.like(
                            "%Status changed% to Resolved%"
                        ),  # Find the specific log
                    )
                    .order_by(ActivityLog.timestamp.desc())
                    .first()
                )

                resolution_time = timedelta(0)
                if resolved_log:  # Use log time if available
                    resolution_time = resolved_log.timestamp - ticket.created_at
                else:  # Fallback: use ticket updated_at (less accurate if edited after resolving)
                    resolution_time = ticket.updated_at - ticket.created_at

                total_resolution_time += resolution_time

            avg_resolution_seconds = (
                total_resolution_time.total_seconds() / resolved_count
            )
            avg_resolution_minutes = avg_resolution_seconds / 60
        else:
            avg_resolution_minutes = 0

        report_data.append(
            {
                "TSR Name": tsr.full_name,
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

    # --- Create Excel ---
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
