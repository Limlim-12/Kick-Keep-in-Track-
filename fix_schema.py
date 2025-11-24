import os
from kick_app import create_app, db
from kick_app.models import TicketAttachment  # Ensure model is loaded

# --- CONFIGURATION ---
# We force the Render DB URL here to ensure we fix the LIVE database
os.environ["DATABASE_URL"] = (
    "postgresql://kick_db_v2_user:mGVN4elj8EobfR10XLp3Sm2nCmIcEQGd@dpg-d4hsjm6mcj7s73c870ag-a.singapore-postgres.render.com/kick_db_v2"
)


def fix():
    print("🚀 Connecting to Render database...")
    app = create_app()

    with app.app_context():
        print("🔧 Checking for missing tables...")

        # db.create_all() checks the database for tables defined in models.py
        # If a table (like ticket_attachments) is missing, it creates it.
        # If a table (like users) already exists, it does nothing.
        db.create_all()

        print(
            "✅ Database schema repaired! 'ticket_attachments' table should now exist."
        )


if __name__ == "__main__":
    fix()
