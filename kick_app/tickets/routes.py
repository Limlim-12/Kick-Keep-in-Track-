from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import func
from . import tickets
from .forms import TicketForm, UpdateTicketForm
from kick_app import db
from kick_app.models import (
    Ticket,
    Client,
    User,
    Region,
    TicketStatus,
    UserRole,
    ActivityLog,
)
from kick_app.decorators import admin_required

# --- Helper Function for Auto-Assignment ---


def get_next_tsr():
    """
    Finds the active TSR with the fewest 'Open' or 'In Progress' tickets.
    This is our core load-balancing logic.
    """

    # Subquery: Count open/in-progress tickets for each TSR
    subquery = (
        db.session.query(
            Ticket.assigned_to_id, func.count(Ticket.id).label("ticket_count")
        )
        .filter(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]))
        .group_by(Ticket.assigned_to_id)
        .subquery()
    )

    # Main Query: Find active TSRs and join with their ticket counts
    tsr_with_counts = (
        db.session.query(User, func.coalesce(subquery.c.ticket_count, 0).label("count"))
        .outerjoin(subquery, User.id == subquery.c.assigned_to_id)
        .filter(User.role == UserRole.TSR, User.is_active == True)
        .order_by(
            func.coalesce(subquery.c.ticket_count, 0).asc()  # Order by count ascending
        )
        .first()
    )  # Get the one with the lowest count

    return tsr_with_counts[0] if tsr_with_counts else None


# --- Ticket Routes ---


@tickets.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_ticket():
    """Admin-only route to create a new ticket."""
    form = TicketForm()
    if form.validate_on_submit():

        # --- ADD THIS PRINT STATEMENT ---
        print("RUNNING NEW TICKET CODE - v2")
        # --- END OF ADDITION ---

        client = form.client.data
        concern_title = form.concern_title.data
        concern_details = form.concern_details.data

        # Auto-generate ticket name per your new format
        ticket_name = (
            f"{client.region.name}_"
            f"{client.account_name}_"                   # <-- Corrected: Name first
            f"{client.account_number}_"                 # <-- Corrected: Number second
            f"{concern_title.replace(' ', '')}"        # <-- Concern title (spaces removed)
        )

        ticket = Ticket(
            ticket_name=ticket_name,
            concern_title=concern_title,
            concern_details=concern_details,
            client_id=client.id,
            created_by_id=current_user.id,
            status=TicketStatus.NEW,
        )

        db.session.add(ticket)
        db.session.commit()  # Commit to get ticket.id

        # Log the creation
        log_creation = ActivityLog(
            action=f"Ticket created by {current_user.full_name}",
            user_id=current_user.id,
            ticket_id=ticket.id,
        )
        db.session.add(log_creation)

        # --- Auto-assignment logic ---
        next_tsr = get_next_tsr()
        if next_tsr:
            ticket.assigned_to_id = next_tsr.id

            # Log the assignment
            log_assign = ActivityLog(
                action=f"Ticket auto-assigned to {next_tsr.full_name}",
                user_id=current_user.id,
                ticket_id=ticket.id,
            )
            db.session.add(log_assign)

            db.session.commit()
            flash(
                f"Ticket created and auto-assigned to {next_tsr.full_name}.", "success"
            )
        else:
            db.session.commit()
            flash(
                "Ticket created but no active TSRs available for assignment.", "warning"
            )

        return redirect(url_for("tickets.all_tickets"))

    # --- ADD THIS 'ELSE' BLOCK ---
    elif request.method == "POST":
        # If form validation fails on POST, flash the errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")
    # --- END OF NEW BLOCK ---

    return render_template("create_ticket.html", title="Create New Ticket", form=form)


@tickets.route("/all")
@login_required
@admin_required
def all_tickets():
    """Admin-only view of all tickets, filterable."""
    page = request.args.get("page", 1, type=int)
    # Simple filtering (we can expand this)
    status_filter = request.args.get("status")

    query = Ticket.query.order_by(Ticket.created_at.desc())

    if status_filter:
        try:
            query = query.filter(Ticket.status == TicketStatus[status_filter.upper()])
        except KeyError:
            flash(f"Invalid status filter '{status_filter}'.", "warning")

    all_tickets = query.paginate(page=page, per_page=15)
    return render_template(
        "all_tickets.html",
        title="All Tickets",
        tickets=all_tickets,
        statuses=TicketStatus,
    )


@tickets.route("/my")
@login_required
def my_tickets():
    """TSR-only view of their assigned tickets."""
    if current_user.role == UserRole.ADMIN:
        # Admins visiting this are redirected to the 'all' page
        return redirect(url_for("tickets.all_tickets"))

    page = request.args.get("page", 1, type=int)

    # Get all tickets assigned to the current user
    # Show Open and In Progress tickets first
    my_tickets = (
        Ticket.query.filter_by(assigned_to_id=current_user.id)
        .order_by(
            db.case(
                (Ticket.status == TicketStatus.OPEN, 0),
                (Ticket.status == TicketStatus.IN_PROGRESS, 1),
                (Ticket.status == TicketStatus.PENDING, 2),
                (Ticket.status == TicketStatus.RESOLVED, 3),
                else_=4,
            ),
            Ticket.updated_at.desc(),
        )
        .paginate(page=page, per_page=15)
    )

    return render_template("my_tickets.html", title="My Tickets", tickets=my_tickets)


@tickets.route("/<int:id>", methods=["GET", "POST"])
@login_required
def view_ticket(id):
    """View ticket details and update (for assigned TSR or Admin)."""
    ticket = Ticket.query.get_or_404(id)

    # Security check: Must be admin or the assigned TSR
    if current_user.role != UserRole.ADMIN and ticket.assigned_to_id != current_user.id:
        flash("You do not have permission to view this ticket.", "danger")
        return redirect(url_for("main.index"))

    # --- START: AUTO-OPEN LOGIC ---
    # If the current user is the assigned TSR and the status is 'New'
    if (
        request.method == "GET"
        and ticket.assigned_to_id == current_user.id
        and ticket.status == TicketStatus.NEW
    ):

        ticket.status = TicketStatus.OPEN
        log_action = f"Ticket status automatically changed to Open by {current_user.full_name} viewing it."
        log_open = ActivityLog(
            action=log_action, user_id=current_user.id, ticket_id=ticket.id
        )
        db.session.add(log_open)
        db.session.commit()
        flash("Ticket status updated to Open.", "info")
        # No redirect needed, just continue rendering the page with the updated status
    # --- END: AUTO-OPEN LOGIC ---

    form = UpdateTicketForm()

    if form.validate_on_submit():
        try:
            new_status_enum = TicketStatus[form.status.data]
            log_action = ""  # For status change log
            something_changed = (
                False  # Flag to track if we need to commit/flash success
            )

            # --- Handle Admin Reassignment ---
            if current_user.role == UserRole.ADMIN:
                new_tsr = form.assigned_tsr.data
                old_tsr_id = ticket.assigned_to_id

                # Check if the assignment has changed
                if new_tsr and old_tsr_id != new_tsr.id:
                    log_reassign_action = f"Ticket reassigned from {ticket.assigned_tsr.full_name if ticket.assigned_tsr else 'Unassigned'} to {new_tsr.full_name} by {current_user.full_name}."
                    log_reassign = ActivityLog(
                        action=log_reassign_action,
                        user_id=current_user.id,
                        ticket_id=ticket.id,
                    )
                    db.session.add(log_reassign)
                    ticket.assigned_to_id = new_tsr.id
                    something_changed = True

                elif not new_tsr and old_tsr_id:
                    log_unassign_action = f"Ticket unassigned from {ticket.assigned_tsr.full_name} by {current_user.full_name}."
                    log_unassign = ActivityLog(
                        action=log_unassign_action,
                        user_id=current_user.id,
                        ticket_id=ticket.id,
                    )
                    db.session.add(log_unassign)
                    ticket.assigned_to_id = None
                    something_changed = True

            # --- Handle RT Ticket Number Update ---
            new_rt_number = (
                form.rt_ticket_number.data.strip() or None
            )  # Get data (strip whitespace) or None if empty/whitespace only
            old_rt_number = ticket.rt_ticket_number

            if new_rt_number != old_rt_number:  # Check if it actually changed
                rt_log_action = ""
                if old_rt_number and new_rt_number:
                    rt_log_action = f"RT Ticket Number changed from '{old_rt_number}' to '{new_rt_number}' by {current_user.full_name}."
                elif new_rt_number:  # Was None, now has value
                    rt_log_action = f"RT Ticket Number '{new_rt_number}' added by {current_user.full_name}."
                elif old_rt_number:  # Had value, now is None (cleared)
                    rt_log_action = f"RT Ticket Number '{old_rt_number}' removed by {current_user.full_name}."

                if rt_log_action:  # Only log if there was a change message
                    log_rt = ActivityLog(
                        action=rt_log_action,
                        user_id=current_user.id,
                        ticket_id=ticket.id,
                    )
                    db.session.add(log_rt)
                ticket.rt_ticket_number = new_rt_number
                something_changed = True

            # --- Log the status change ---
            if ticket.status != new_status_enum:
                # Prepare status change message, will be added as a log entry later
                log_action = (
                    f"Status changed from {ticket.status.value} to {new_status_enum.value} "
                    f"by {current_user.full_name}."
                )
                ticket.status = new_status_enum
                something_changed = True

            # --- Add the remarks ---
            if form.remarks.data:
                remark_log_action = (
                    f"Remark added by {current_user.full_name}: {form.remarks.data}"
                )
                log_remark = ActivityLog(
                    action=remark_log_action,
                    user_id=current_user.id,
                    ticket_id=ticket.id,
                )
                db.session.add(log_remark)
                something_changed = True  # Remarks count as a change

            # --- Commit Status Change Log (if status changed) ---
            # This is done separately to keep status change and remarks distinct in log
            if log_action:
                log_status = ActivityLog(
                    action=log_action.strip(),  # Use the message prepared earlier
                    user_id=current_user.id,
                    ticket_id=ticket.id,
                )
                db.session.add(log_status)

            # --- Final Commit and Flash ---
            if something_changed:
                db.session.commit()
                flash("Ticket updated successfully.", "success")
            else:
                flash("No changes detected.", "info")  # Inform user if nothing changed

            return redirect(url_for("tickets.view_ticket", id=id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating ticket: {e}", "danger")

    # --- Pre-populate form on GET request ---
    if request.method == "GET":
        form.status.data = ticket.status.name
        form.rt_ticket_number.data = ticket.rt_ticket_number  # Pre-fill RT number
        if ticket.assigned_tsr:
            form.assigned_tsr.data = ticket.assigned_tsr

    # Get all activity logs for this ticket
    logs = ticket.logs.order_by(ActivityLog.timestamp.asc()).all()

    return render_template(
        "view_ticket.html",
        title=f'Ticket: {ticket.ticket_name}',  # Use concern_title for page title
        ticket=ticket,
        form=form,
        logs=logs,
    )


@tickets.route("/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_ticket(id):
    """Admin-only route to delete a ticket."""
    ticket = Ticket.query.get_or_404(id)

    # Manually delete dependent activity logs first
    # This prevents a database error
    ActivityLog.query.filter_by(ticket_id=ticket.id).delete()

    # Now, safely delete the ticket
    db.session.delete(ticket)
    db.session.commit()

    flash(f'Ticket "{ticket.concern_title}" has been permanently deleted.', "success")
    return redirect(url_for("tickets.all_tickets"))
