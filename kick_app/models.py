from . import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app


# --- Enums for Choices ---
# Using Enums makes the choices clean and readable
class UserRole(enum.Enum):
    ADMIN = "Admin"
    TSR = "TSR"


class TicketStatus(enum.Enum):
    NEW = "New"  # <-- Add this line
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    PENDING = "Pending"


# --- Flask-Login User Loader ---
# This function is required by Flask-Login to load a user from session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Model Definitions ---


class User(db.Model, UserMixin):
    """Stores user accounts (Admins and TSRs)."""

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    # --- UPDATED/NEW FIELDS ---
    employee_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.Enum(UserRole), default=UserRole.TSR, nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- REMOVED/RENAMED ---
    # 'username' field is replaced by 'employee_id'

    # Relationships (these are the same)
    assigned_tickets = db.relationship(
        "Ticket",
        back_populates="assigned_tsr",
        lazy="dynamic",
        foreign_keys="Ticket.assigned_to_id",
    )
    created_tickets = db.relationship(
        "Ticket",
        back_populates="creator",
        lazy="dynamic",
        foreign_keys="Ticket.created_by_id",
    )
    activity_logs = db.relationship(
        "ActivityLog", back_populates="user", lazy="dynamic"
    )
    announcements = db.relationship(
        "Announcement", back_populates="author", lazy="dynamic"
    )
    email_logs = db.relationship("EmailLog", back_populates="author", lazy="dynamic")

    def __repr__(self):
        # Updated repr
        return f"<User {self.full_name} ({self.employee_id})>"

    # --- ADD THIS HELPER METHOD ---
    def get_id(self):
        """
        Required by Flask-Login. Returns a string representation of the user ID.
        We'll use employee_id as the natural key for login, but Flask-Login
        still needs the primary key (id) for session management.
        """
        return str(self.id)

    # --- ADDED PASSWORD METHODS ---
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Ensure hash exists before checking
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False


class Region(db.Model):
    """Reference list for all regions."""

    __tablename__ = "regions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # Relationship
    clients = db.relationship("Client", back_populates="region", lazy="dynamic")

    def __repr__(self):
        return f"<Region {self.name}>"


class Client(db.Model):
    """Stores subscriber/client details."""

    __tablename__ = "clients"
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    account_name = db.Column(db.String(200), nullable=False, index=True)
    status = db.Column(db.String(50), default="Active")
    plan_rate = db.Column(db.Float, nullable=False, default=0.0)

    # Foreign Key
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False)

    # Relationships
    region = db.relationship("Region", back_populates="clients")
    tickets = db.relationship("Ticket", back_populates="client", lazy="dynamic")

    def __repr__(self):
        return f"<Client {self.account_name} ({self.account_number})>"


class Ticket(db.Model):
    """Contains all ticket information."""

    __tablename__ = "tickets"
    id = db.Column(db.Integer, primary_key=True)
    ticket_name = db.Column(
        db.String(300), unique=True
    )  # The "Region_AccountName_Num_Concern"
    concern_title = db.Column(db.String(255), nullable=False)
    concern_details = db.Column(db.Text, nullable=False)  # Renamed from 'concern'
    rt_ticket_number = db.Column(
        db.String(100), nullable=True, index=True
    )  # Optional RT ticket number
    status = db.Column(
        db.Enum(TicketStatus), default=TicketStatus.NEW, nullable=False, index=True
    )  # Default changed to NEW
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Foreign Keys
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )  # Can be unassigned
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id")
    )  # e.g., Admin who created it

    # Relationships
    client = db.relationship("Client", back_populates="tickets")
    assigned_tsr = db.relationship(
        "User", back_populates="assigned_tickets", foreign_keys=[assigned_to_id]
    )
    creator = db.relationship(
        "User", back_populates="created_tickets", foreign_keys=[created_by_id]
    )
    logs = db.relationship("ActivityLog", back_populates="ticket", lazy="dynamic")
    
    email_logs = db.relationship("EmailLog", back_populates="ticket", lazy="dynamic")

    def __repr__(self):
        return f"<Ticket {self.id} - {self.status.value}>"


class ActivityLog(db.Model):
    """Stores actions taken on tickets and users."""

    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(
        db.String(255), nullable=False
    )  # e.g., "Created ticket", "Assigned to TSR_Name"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"))

    # Relationships
    user = db.relationship("User", back_populates="activity_logs")
    ticket = db.relationship("Ticket", back_populates="logs")

    def __repr__(self):
        return f"<Log: {self.action}>"


class Announcement(db.Model):
    """Stores admin messages visible to all TSRs."""

    __tablename__ = "announcements"
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Foreign Key
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # Who posted it

    # Relationship
    author = db.relationship("User", back_populates="announcements")


class EmailLog(db.Model):
    """Stores a log of emails sent to clients."""

    __tablename__ = "email_logs"
    id = db.Column(db.Integer, primary_key=True)
    email_content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Foreign Keys
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )  # Who logged it

    # Relationships
    # This relationship links back to the corrected one above
    ticket = db.relationship("Ticket", back_populates="email_logs")
    author = db.relationship("User", back_populates="email_logs")

    def __repr__(self):
        return f"<EmailLog {self.id} for Ticket {self.ticket_id}>"
