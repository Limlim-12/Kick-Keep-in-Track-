import os
import pandas as pd
from sqlalchemy import create_engine

# This is your Render Database URL
DB_URL = "postgresql://kick_db_user:MsUyd4dZXaeJOTebKCKfzIEmIM5Zz2Ct@dpg-d3td070dl3ps73eas7h0-a.singapore-postgres.render.com/kick_db"


def backup():
    print("🚀 Connecting to Render database...")
    try:
        # Connect to the database
        engine = create_engine(DB_URL)

        # List of tables to backup
        tables = [
            "users",
            "regions",
            "clients",
            "tickets",
            "activity_logs",
            "announcements",
        ]

        # Create a folder for the backup
        if not os.path.exists("rescue_backup"):
            os.makedirs("rescue_backup")

        print("💾 Starting backup...")

        for table in tables:
            try:
                # Read table data into a pandas DataFrame
                df = pd.read_sql_table(table, engine)

                # Save to CSV file
                filename = f"rescue_backup/{table}.csv"
                df.to_csv(filename, index=False)
                print(f"   ✅ Saved {len(df)} rows from '{table}' to {filename}")

            except ValueError:
                print(
                    f"   ⚠️  Table '{table}' not found (might be empty or not created)."
                )
            except Exception as e:
                print(f"   ❌ Error backing up '{table}': {e}")

        print("\n🎉 Backup Complete! Your data is in the 'rescue_backup' folder.")
        print("⚠️  NOW GO DELETE THE PAID DATABASE ON RENDER TO STOP CHARGES! ⚠️")

    except Exception as e:
        print(f"\n❌ Critical Error: Could not connect to database.\n{e}")
        print("Try running: pip install psycopg2-binary sqlalchemy pandas")


if __name__ == "__main__":
    backup()
