import pandas as pd
from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
)  # Removed current_app
from flask_login import login_required, current_user
from . import admin
from .forms import ClientForm, ExcelUploadForm, AnnouncementForm, ReportForm
from .. import db

# CORRECTED IMPORT: Added User and UserRole
from kick_app.models import Client, Region, User, UserRole, Announcement
from kick_app.decorators import admin_required
from werkzeug.utils import secure_filename

# import os # Removed os


@admin.route("/clients", methods=["GET", "POST"])
@login_required
@admin_required
def client_list():
    """
    Display client list, handle search, and handle Excel upload.
    """
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("search", "")

    upload_form = ExcelUploadForm()

    # Handle Excel Upload
    if upload_form.validate_on_submit():
        try:
            f = upload_form.excel_file.data
            filename = secure_filename(f.filename)

            # Use pandas to read the Excel file
            df = pd.read_excel(f)

            # Expected columns - adjust as needed
            required_columns = [
                "account_number",
                "account_name",
                "region_name",
                "status",
            ]

            if not all(col in df.columns for col in required_columns):
                flash(
                    "Excel file is missing required columns: "
                    f'{", ".join(required_columns)}',
                    "danger",
                )
                return redirect(url_for("admin.client_list"))

            clients_added = 0
            for index, row in df.iterrows():
                # Find the region by name
                region = Region.query.filter_by(name=row["region_name"]).first()
                if not region:
                    # If region doesn't exist, create it
                    region = Region(name=row["region_name"])
                    db.session.add(region)
                    # We commit here to get the region.id
                    db.session.commit()

                # Check if client already exists
                existing_client = Client.query.filter_by(
                    account_number=str(row["account_number"])
                ).first()
                if not existing_client:
                    client = Client(
                        account_number=str(row["account_number"]),
                        account_name=row["account_name"],
                        region_id=region.id,
                        status=row["status"],
                    )
                    db.session.add(client)
                    clients_added += 1

            db.session.commit()
            flash(f"Successfully imported {clients_added} new clients.", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during import: {e}", "danger")

        return redirect(url_for("admin.client_list"))

    # Handle Search
    if search_query:
        search_term = f"%{search_query}%"
        clients = (
            Client.query.join(Region)
            .filter(
                db.or_(
                    Client.account_number.like(search_term),
                    Client.account_name.like(search_term),
                    Region.name.like(search_term),
                )
            )
            .paginate(page=page, per_page=10)
        )
    else:
        clients = Client.query.paginate(page=page, per_page=10)

    return render_template(
        "client_list.html",
        title="Client Management",
        clients=clients,
        upload_form=upload_form,
        search_query=search_query,
    )


@admin.route("/client/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_client():
    """Handle adding a new client."""
    form = ClientForm()
    if form.validate_on_submit():
        # Check if account number already exists
        existing_client = Client.query.filter_by(
            account_number=form.account_number.data
        ).first()
        if existing_client:
            flash("An account with this number already exists.", "danger")
        else:
            client = Client(
                account_number=form.account_number.data,
                account_name=form.account_name.data,
                region=form.region.data,
                status=form.status.data,
            )
            db.session.add(client)
            db.session.commit()
            flash("New client has been added.", "success")
            return redirect(url_for("admin.client_list"))
    return render_template("client_form.html", title="Add Client", form=form)


@admin.route("/client/edit/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_client(id):
    """Handle editing an existing client."""
    client = Client.query.get_or_404(id)
    form = ClientForm(obj=client)  # Pre-populate form with client data

    if form.validate_on_submit():
        # Check if new account number conflicts with another client
        if client.account_number != form.account_number.data:
            existing_client = Client.query.filter_by(
                account_number=form.account_number.data
            ).first()
            if existing_client:
                flash("An account with this new number already exists.", "danger")
                return render_template(
                    "client_form.html", title="Edit Client", form=form
                )

        client.account_number = form.account_number.data
        client.account_name = form.account_name.data
        client.region = form.region.data
        client.status = form.status.data
        db.session.commit()
        flash("Client details have been updated.", "success")
        return redirect(url_for("admin.client_list"))

    return render_template("client_form.html", title="Edit Client", form=form)


@admin.route("/client/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_client(id):
    """Handle deleting a client."""
    client = Client.query.get_or_404(id)

    # --- START OF FIX: Check for associated tickets ---
    # We use .first() as it's an efficient way to check if at least one ticket exists
    if client.tickets.first():
        flash(
            f"Cannot delete client '{client.account_name}'. They have existing tickets. "
            "Please resolve or reassign their tickets first.",
            "danger",
        )
    # --- END OF FIX ---
    else:
        # This part only runs if the 'if' condition is false
        db.session.delete(client)
        db.session.commit()
        flash("Client has been deleted.", "success")

    return redirect(url_for("admin.client_list"))


@admin.route("/users")
@login_required
@admin_required
def user_list():
    """Display list of all users, with pending users first."""
    # Order by is_active (False first) then by creation date
    all_users = User.query.order_by(User.is_active.asc(), User.created_at.desc()).all()
    return render_template("user_list.html", title="User Management", users=all_users)


@admin.route("/users/approve/<int:id>", methods=["POST"])
@login_required
@admin_required
def approve_user(id):
    """Approve a pending TSR."""
    user = User.query.get_or_404(id)
    if user.role == UserRole.TSR and not user.is_active:
        user.is_active = True
        db.session.commit()
        flash(
            f"User {user.full_name} ({user.employee_id}) has been approved.", "success"
        )
    else:
        flash("User is already active or is an Admin.", "warning")
    return redirect(url_for("admin.user_list"))


@admin.route("/users/reject/<int:id>", methods=["POST"])
@login_required
@admin_required
def reject_user(id):
    """Reject (delete) a pending TSR."""
    user = User.query.get_or_404(id)
    if not user.is_active and user.role != UserRole.ADMIN:
        db.session.delete(user)
        db.session.commit()
        flash(
            f"User {user.full_name} ({user.employee_id}) has been rejected and deleted.",
            "success",
        )
    else:
        flash("Cannot delete an active user or an Admin.", "danger")
    return redirect(url_for("admin.user_list"))


# --- ANNOUNCEMENT ROUTES ---


@admin.route("/announcements", methods=["GET", "POST"])
@login_required
@admin_required
def manage_announcements():
    """Admin page to view, create, and delete announcements."""
    form = AnnouncementForm()

    if form.validate_on_submit():
        announcement = Announcement(message=form.message.data, user_id=current_user.id)
        db.session.add(announcement)
        db.session.commit()
        flash("New announcement has been posted.", "success")
        return redirect(url_for("admin.manage_announcements"))

    # Get all announcements, newest first
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()

    return render_template(
        "announcements.html",
        title="Announcement Management",
        form=form,
        announcements=announcements,
    )


@admin.route("/announcements/toggle/<int:id>", methods=["POST"])
@login_required
@admin_required
def toggle_announcement(id):
    """Toggles the 'is_active' status of an announcement."""
    announcement = Announcement.query.get_or_404(id)
    announcement.is_active = not announcement.is_active
    db.session.commit()
    status = "activated" if announcement.is_active else "deactivated"
    flash(f"Announcement has been {status}.", "info")
    return redirect(url_for("admin.manage_announcements"))


@admin.route("/announcements/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_announcement(id):
    """Deletes an announcement."""
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    flash("Announcement has been permanently deleted.", "success")
    return redirect(url_for("admin.manage_announcements"))


@admin.route("/reports", methods=["GET", "POST"])
@login_required
@admin_required
def reports():
    """Admin page for generating reports."""
    form = ReportForm()

    if form.validate_on_submit():
        # ---- IMPORTANT: Define variables *inside* the 'if' block ----
        start_date = form.start_date.data
        end_date = form.end_date.data
        # -----------------------------------------------------------

        if form.submit_tickets.data:
            # User clicked 'Generate Ticket Report'
            return redirect(
                url_for("api.export_tickets", start_date=start_date, end_date=end_date)
            )
        elif form.submit_tsr.data:
            # User clicked 'Generate TSR Performance Report'
            return redirect(
                url_for(
                    "api.export_tsr_performance",
                    start_date=start_date,
                    end_date=end_date,
                )
            )

    # If it's a GET request or validation failed, render the form
    return render_template("reports.html", title="Reporting Tools", form=form)
