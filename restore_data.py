import pandas as pd
from sqlalchemy import create_engine, text
import os

# Grab the V3 URL from your environment variable
NEW_DB_URL = os.environ.get("DATABASE_URL")
BACKUP_FOLDER = "rescue_backup"


def restore():
    if not NEW_DB_URL:
        print("❌ Error: DATABASE_URL is not set.")
        print("   Run this in terminal first: $env:DATABASE_URL = 'YOUR_V3_URL'")
        return

    print(f"🚀 Uploading to NEW database: {NEW_DB_URL.split('@')[-1]} ...")
    engine = create_engine(NEW_DB_URL)

    # Order is critical! Parents before children.
    tables = [
        "regions",
        "users",
        "clients",
        "tickets",
        "activity_logs",
        "email_logs",  # <-- Includes Email Logs
        "ticket_attachments",  # <-- Includes Attachments
        "announcements",
    ]

    with engine.connect() as conn:
        for table in tables:
            file_path = f"{BACKUP_FOLDER}/{table}.csv"
            if os.path.exists(file_path):
                print(f"   Processing '{table}'...")
                try:
                    df = pd.read_csv(file_path)

                    if df.empty:
                        print(f"      ⚠️  CSV is empty. Skipping.")
                        continue

                    # Insert data
                    df.to_sql(table, conn, if_exists="append", index=False)
                    print(f"      ✅ Restored {len(df)} rows.")

                    # Fix ID counters so new entries don't crash
                    if "id" in df.columns:
                        max_id = df["id"].max()
                        if pd.notna(max_id):
                            seq_name = f"{table}_id_seq"
                            # Reset the sequence
                            conn.execute(
                                text(f"SELECT setval('{seq_name}', {int(max_id)})")
                            )
                            print(f"      🔧 Fixed ID counter.")

                except Exception as e:
                    print(f"      ❌ Error uploading {table}: {e}")
            else:
                print(f"   ⚠️  File {table}.csv not found. Skipping.")

        conn.commit()
    print("\n🎉 RESTORE COMPLETE! Your kick-db-v3 is live.")


if __name__ == "__main__":
    restore()
