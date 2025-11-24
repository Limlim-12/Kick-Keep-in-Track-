import pandas as pd
import os
from sqlalchemy import create_engine, text

# This is your Render Database URL
NEW_DB_URL = "postgresql://kick_db_v2_user:mGVN4elj8EobfR10XLp3Sm2nCmIcEQGd@dpg-d4hsjm6mcj7s73c870ag-a.singapore-postgres.render.com/kick_db_v2"


def restore():
    print("🚀 Connecting to new Render database...")
    try:
        engine = create_engine(NEW_DB_URL)

        # Order matters! Parents before children.
        tables_order = [
            "regions",
            "users",
            "announcements",
            "clients",
            "tickets",
            "activity_logs",
        ]

        print("💾 Starting restore process...")

        with engine.connect() as conn:
            for table in tables_order:
                try:
                    print(f"   Processing '{table}'...")

                    # 1. Read CSV
                    csv_path = f"rescue_backup/{table}.csv"
                    if not os.path.exists(csv_path):
                        print(f"      ⚠️  File {csv_path} not found. Skipping.")
                        continue

                    df = pd.read_csv(csv_path)

                    if df.empty:
                        print(f"      ⚠️  CSV for '{table}' is empty. Skipping.")
                        continue

                    # 2. FIX MISSING COLUMNS (The Patch)
                    # Fix Tickets: Add 'email_sent' if missing
                    if table == "tickets" and "email_sent" not in df.columns:
                        print("      🔧 Patching missing 'email_sent' column...")
                        df["email_sent"] = False

                    # Fix Clients: Add 'plan_rate' if missing
                    if table == "clients" and "plan_rate" not in df.columns:
                        print("      🔧 Patching missing 'plan_rate' column...")
                        df["plan_rate"] = 0.0

                    # 3. Insert data
                    df.to_sql(table, engine, if_exists="append", index=False)
                    print(f"      ✅ Restored {len(df)} rows to '{table}'.")

                    # 4. Reset Auto-Increment ID (Sequence)
                    try:
                        # PostgreSQL command to sync the ID counter
                        query = text(
                            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id)+1, 1), false) FROM {table};"
                        )
                        conn.execute(query)
                        print(f"      🔄 ID sequence reset for '{table}'.")
                    except Exception as seq_e:
                        # Some tables might not have an ID sequence, which is fine
                        print(
                            f"      ℹ️  Note: Sequence reset skipped (usually fine): {seq_e}"
                        )

                except Exception as e:
                    print(f"      ❌ Error restoring '{table}': {e}")

            conn.commit()

        print("\n🎉 RESTORE COMPLETE! Your app should be fully functional.")

    except Exception as e:
        print(f"\n❌ Connection Error: {e}")


if __name__ == "__main__":
    restore()
