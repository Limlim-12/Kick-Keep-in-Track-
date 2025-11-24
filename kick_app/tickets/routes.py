from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from . import tickets
from .forms import TicketForm, UpdateTicketForm, EmailLogForm, AttachmentForm
from .. import db
from ..models import (
    Ticket,
    Client,
    User,
    Region,
    TicketStatus,
    UserRole,
    ActivityLog,
    EmailLog,
    TicketAttachment,
)
from ..decorators import admin_required
import pytz
from datetime import datetime


# --- Helper Function for Auto-Assignment ---
def get_next_tsr():
    subquery = (
        db.session.query(
            Ticket.assigned_to_id, func.count(Ticket.id).label("ticket_count")
        )
        .filter(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]))
        .group_by(Ticket.assigned_to_id)
        .subquery()
    )
    tsr_with_counts = (
        db.session.query(User, func.coalesce(subquery.c.ticket_count, 0).label("count"))
        .outerjoin(subquery, User.id == subquery.c.assigned_to_id)
        .filter(User.role == UserRole.TSR, User.is_active == True)
        .order_by(func.coalesce(subquery.c.ticket_count, 0).asc())
        .first()
    )
    return tsr_with_counts[0] if tsr_with_counts else None


# --- Ticket Routes ---


@tickets.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_ticket():
    form = TicketForm()
    if form.validate_on_submit():
        client = form.client.data
        concern_title = form.concern_title.data
        concern_details = form.concern_details.data

        # Unique timestamp for ticket name
        timestamp_str = str(int(datetime.utcnow().timestamp()))

        ticket_name = (
            f"{client.region.name}_"
            f"{client.account_name}_"
            f"{client.account_number}_"
            f"{concern_title.replace(' ', '')}_"
            f"{timestamp_str}"
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
        db.session.commit()

        log_creation = ActivityLog(
            action=f"Ticket created by {current_user.full_name}",
            user_id=current_user.id,
            ticket_id=ticket.id,
        )
        db.session.add(log_creation)

        next_tsr = get_next_tsr()
        if next_tsr:
            ticket.assigned_to_id = next_tsr.id
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

    elif request.method == "POST":
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")

    return render_template("create_ticket.html", title="Create New Ticket", form=form)


@tickets.route("/all")
@login_required
@admin_required
def all_tickets():
    """Admin-only view of all tickets with ADVANCED SEARCH."""
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status")
    search_query = request.args.get("search", "").strip()

    # Join Client, Region, AND outerjoin User (for assigned TSR search)
    query = (
        Ticket.query.join(Client)
        .join(Region)
        .outerjoin(
            User, Ticket.assigned_to_id == User.id
        )  # Join User table to search TSR names
        .order_by(Ticket.created_at.desc())
    )

    # Apply Status Filter (Dropdown)
    if status_filter:
        try:
            query = query.filter(Ticket.status == TicketStatus[status_filter.upper()])
        except KeyError:
            flash(f"Invalid status filter '{status_filter}'.", "warning")

    # --- SMART SEARCH ENGINE ---
    if search_query:
        search_term = f"%{search_query}%"

        # Use ILIKE for case-insensitive search (PostgreSQL friendly)
        query = query.filter(
            or_(
                Ticket.ticket_name.ilike(search_term),  # Ticket Name
                Ticket.concern_title.ilike(search_term),  # Concern
                Ticket.rt_ticket_number.ilike(search_term),  # RT Number
                Client.account_name.ilike(search_term),  # Client Name
                Client.account_number.ilike(search_term),  # Account Number
                Region.name.ilike(search_term),  # Region
                User.full_name.ilike(search_term),  # Assigned TSR Name
                # Cast Enum status to string to allow searching "RESOLVED" or "OPEN"
                db.cast(Ticket.status, db.String).ilike(search_term),
            )
        )

    all_tickets = query.paginate(page=page, per_page=15, error_out=False)
    return render_template(
        "all_tickets.html",
        title="All Tickets",
        tickets=all_tickets,
        statuses=TicketStatus,
        search_query=search_query,
    )


@tickets.route("/my")
@login_required
def my_tickets():
    """TSR-only view with ADVANCED SEARCH."""
    if current_user.role == UserRole.ADMIN:
        return redirect(url_for("tickets.all_tickets"))

    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("search", "").strip()

    # Base query for user's tickets
    query = Ticket.query.filter_by(assigned_to_id=current_user.id)

    # --- SMART SEARCH ENGINE ---
    if search_query:
        search_term = f"%{search_query}%"
        query = (
            query.join(Client)
            .join(Region)
            .filter(
                or_(
                    Ticket.ticket_name.ilike(search_term),
                    Ticket.concern_title.ilike(search_term),
                    Ticket.rt_ticket_number.ilike(search_term),
                    Client.account_name.ilike(search_term),
                    Client.account_number.ilike(search_term),
                    Region.name.ilike(search_term),
                    db.cast(Ticket.status, db.String).ilike(search_term),
                )
            )
        )

    # Apply sorting
    query = query.order_by(
        db.case(
            (Ticket.status == TicketStatus.NEW, -1),
            (Ticket.status == TicketStatus.OPEN, 0),
            (Ticket.status == TicketStatus.IN_PROGRESS, 1),
            (Ticket.status == TicketStatus.PENDING, 2),
            (Ticket.status == TicketStatus.RESOLVED, 3),
            else_=4,
        ),
        Ticket.updated_at.desc(),
    )

    my_tickets = query.paginate(page=page, per_page=15, error_out=False)

    return render_template(
        "my_tickets.html",
        title="My Tickets",
        tickets=my_tickets,
        search_query=search_query,
    )


@tickets.route("/<int:id>", methods=["GET", "POST"])
@login_required
def view_ticket(id):
    ticket = Ticket.query.get_or_404(id)
    if current_user.role != UserRole.ADMIN and ticket.assigned_to_id != current_user.id:
        flash("You do not have permission to view this ticket.", "danger")
        return redirect(url_for("main.index"))

    # Auto-open logic
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

    form = UpdateTicketForm()
    email_form = EmailLogForm()
    attachment_form = AttachmentForm()

    # --- NEW: Handle Attachment Upload ---
    if attachment_form.submit_attachment.data and attachment_form.validate_on_submit():
        try:
            f = attachment_form.file.data
            original_filename = secure_filename(f.filename)

            # Create a unique filename: ticketID_timestamp_filename
            timestamp = int(datetime.utcnow().timestamp())
            unique_filename = f"{ticket.id}_{timestamp}_{original_filename}"

            # Define upload path: kick_app/static/uploads/tickets
            upload_dir = os.path.join(
                current_app.root_path, "static", "uploads", "tickets"
            )
            os.makedirs(upload_dir, exist_ok=True)  # Create dir if not exists

            # Save the file
            file_path = os.path.join(upload_dir, unique_filename)
            f.save(file_path)

            # Save to DB
            attachment = TicketAttachment(
                filename=original_filename,
                filepath=f"uploads/tickets/{unique_filename}",  # Relative to static folder
                ticket_id=ticket.id,
                uploader_id=current_user.id,
            )
            db.session.add(attachment)

            # Log it
            log_activity = ActivityLog(
                action=f"Uploaded attachment: {original_filename}",
                user_id=current_user.id,
                ticket_id=ticket.id,
            )
            db.session.add(log_activity)

            db.session.commit()
            flash(f"File '{original_filename}' uploaded successfully.", "success")
            return redirect(url_for("tickets.view_ticket", id=id))

        except Exception as e:
            db.session.rollback()
            flash(f"Error uploading file: {e}", "danger")

    if email_form.submit_email_log.data and email_form.validate_on_submit():
        try:
            pht_tz = pytz.timezone("Asia/Manila")
            naive_dt = email_form.sent_at.data
            if naive_dt.tzinfo is None:
                pht_dt = pht_tz.localize(naive_dt)
            else:
                pht_dt = naive_dt.astimezone(pht_tz)

            utc_dt = pht_dt.astimezone(pytz.utc)

            new_log = EmailLog(
                email_content=email_form.email_content.data,
                sent_at=utc_dt,
                ticket_id=ticket.id,
                user_id=current_user.id,
            )
            db.session.add(new_log)

            log_activity = ActivityLog(
                action=f"Email log added by {current_user.full_name}.",
                user_id=current_user.id,
                ticket_id=ticket.id,
            )
            db.session.add(log_activity)

            db.session.commit()
            flash("New email log entry has been added.", "success")
            return redirect(url_for("tickets.view_ticket", id=id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error logging email: {e}", "danger")

    elif form.submit.data and form.validate_on_submit():
        try:
            new_status_enum = TicketStatus[form.status.data]
            log_action = ""
            something_changed = False

            if current_user.role == UserRole.ADMIN:
                new_tsr = form.assigned_tsr.data
                old_tsr_id = ticket.assigned_to_id
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

            new_rt_number = form.rt_ticket_number.data.strip() or None
            old_rt_number = ticket.rt_ticket_number
            if new_rt_number != old_rt_number:
                rt_log_action = ""
                if old_rt_number and new_rt_number:
                    rt_log_action = f"RT Ticket Number changed from '{old_rt_number}' to '{new_rt_number}' by {current_user.full_name}."
                elif new_rt_number:
                    rt_log_action = f"RT Ticket Number '{new_rt_number}' added by {current_user.full_name}."
                elif old_rt_number:
                    rt_log_action = f"RT Ticket Number '{old_rt_number}' removed by {current_user.full_name}."
                if rt_log_action:
                    log_rt = ActivityLog(
                        action=rt_log_action,
                        user_id=current_user.id,
                        ticket_id=ticket.id,
                    )
                    db.session.add(log_rt)
                ticket.rt_ticket_number = new_rt_number
                something_changed = True

            if ticket.status != new_status_enum:
                log_action = (
                    f"Status changed from {ticket.status.value} to {new_status_enum.value} "
                    f"by {current_user.full_name}."
                )
                ticket.status = new_status_enum
                something_changed = True

            if form.remarks.data:
                last_remark_log = (
                    ActivityLog.query.filter(
                        ActivityLog.ticket_id == ticket.id,
                        ActivityLog.action.like(
                            f"Remark added by {current_user.full_name}:%"
                        ),
                    )
                    .order_by(ActivityLog.timestamp.desc())
                    .first()
                )

                if (
                    not last_remark_log
                    or last_remark_log.action
                    != f"Remark added by {current_user.full_name}: {form.remarks.data}"
                ):
                    remark_log_action = (
                        f"Remark added by {current_user.full_name}: {form.remarks.data}"
                    )
                    log_remark = ActivityLog(
                        action=remark_log_action,
                        user_id=current_user.id,
                        ticket_id=ticket.id,
                    )
                    db.session.add(log_remark)
                    something_changed = True

            if log_action:
                log_status = ActivityLog(
                    action=log_action.strip(),
                    user_id=current_user.id,
                    ticket_id=ticket.id,
                )
                db.session.add(log_status)

            if something_changed:
                db.session.commit()
                flash("Ticket updated successfully.", "success")
            else:
                flash("No changes detected.", "info")
            return redirect(url_for("tickets.view_ticket", id=id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating ticket: {e}", "danger")

    if request.method == "GET" or not form.validate_on_submit():
        form.status.data = ticket.status.name
        form.rt_ticket_number.data = ticket.rt_ticket_number
        if ticket.assigned_tsr:
            form.assigned_tsr.data = ticket.assigned_tsr

    logs = ticket.logs.order_by(ActivityLog.timestamp.asc()).all()
    email_logs = ticket.email_logs.order_by(EmailLog.sent_at.desc()).all()
    attachments = ticket.attachments.order_by(
        TicketAttachment.uploaded_at.desc()
    ).all()  # Get attachments

    return render_template(
        "view_ticket.html",
        title=f"Ticket: {ticket.ticket_name}",
        ticket=ticket,
        form=form,
        email_form=email_form,
        attachment_form=attachment_form,
        logs=logs,
        email_logs=email_logs,
        attachments=attachments,
    )


@tickets.route("/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_ticket(id):
    ticket = Ticket.query.get_or_404(id)
    ActivityLog.query.filter_by(ticket_id=ticket.id).delete()
    EmailLog.query.filter_by(ticket_id=ticket.id).delete()
    db.session.delete(ticket)
    db.session.commit()
    flash(f'Ticket "{ticket.concern_title}" has been permanently deleted.', "success")
    return redirect(url_for("tickets.all_tickets"))
