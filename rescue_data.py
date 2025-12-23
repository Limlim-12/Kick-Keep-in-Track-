import os
import pandas as pd
from sqlalchemy import create_engine

# --- CONFIGURATION ---
# I added '.singapore-postgres.render.com' to make it accessible from your laptop
DB_URL = "postgresql://kick_db_v2_user:mGVN4elj8EobfR10XLp3Sm2nCmIcEQGd@dpg-d4hsjm6mcj7s73c870ag-a.singapore-postgres.render.com/kick_db_v2"

# Folder to save CSVs
BACKUP_FOLDER = "rescue_backup"


def backup():
    print(f"🚀 Connecting to database: kick_db_v2 (External) ...")

    try:
        engine = create_engine(DB_URL)

        # We need ALL 8 tables for the new system
        tables = [
            "regions",
            "users",
            "clients",
            "tickets",
            "activity_logs",
            "email_logs",  # New Feature
            "ticket_attachments",  # New Feature
            "announcements",
        ]

        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)
            print(f"📂 Created folder: {BACKUP_FOLDER}")

        print("💾 Starting backup...")

        with engine.connect() as conn:
            for table in tables:
                try:
                    df = pd.read_sql(f"SELECT * FROM {table}", conn)
                    filename = f"{BACKUP_FOLDER}/{table}.csv"
                    df.to_csv(filename, index=False)
                    print(f"   ✅ Saved {len(df)} rows from '{table}'")
                except Exception as e:
                    print(f"   ⚠️  Could not backup '{table}' (might be empty): {e}")

        print(f"\n🎉 Backup Complete! Check the '{BACKUP_FOLDER}' folder.")
        print(
            "🔎 Please open 'tickets.csv' and check if your recent tickets are there!"
        )

    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
        print(
            "Note: If this fails, go to Render Dashboard -> Connect -> External Connection and copy that URL."
        )


if __name__ == "__main__":
    backup()
