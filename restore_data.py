import pandas as pd
from sqlalchemy import create_engine, text

# ---------------------------------------------------------
# PASTE YOUR NEW FREE DATABASE EXTERNAL URL HERE
# ---------------------------------------------------------
NEW_DB_URL = "postgresql://kick_db_v2_user:mGVN4elj8EobfR10XLp3Sm2nCmIcEQGd@dpg-d4hsjm6mcj7s73c870ag-a.singapore-postgres.render.com/kick_db_v2"
# ---------------------------------------------------------


def restore():
    print("🚀 Connecting to new Render database...")
    try:
        engine = create_engine(NEW_DB_URL)

        # Order matters! We must restore parents before children.
        # 1. Independent tables
        # 2. Tables with Foreign Keys to group 1
        # 3. Tables with Foreign Keys to group 2
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

                    # Read CSV
                    csv_path = f"rescue_backup/{table}.csv"
                    df = pd.read_csv(csv_path)

                    if df.empty:
                        print(f"      ⚠️  CSV for '{table}' is empty. Skipping.")
                        continue

                    # Insert data (if_exists='append' adds to the empty tables created by deploy)
                    # index=False because we don't want the pandas index, we want the CSV's 'id' column
                    df.to_sql(table, engine, if_exists="append", index=False)

                    print(f"      ✅ Restored {len(df)} rows to '{table}'.")

                    # CRITICAL: Reset the auto-increment ID counter (Sequence)
                    # If we don't do this, the next new ticket you create will crash the app.
                    try:
                        # PostgreSQL specific command to fix ID sync
                        query = text(
                            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id)+1, 1), false) FROM {table};"
                        )
                        conn.execute(query)
                        print(f"      🔄 ID sequence reset for '{table}'.")
                    except Exception as seq_e:
                        print(
                            f"      ⚠️  Could not reset sequence (might not have an ID column): {seq_e}"
                        )

                except FileNotFoundError:
                    print(f"      ❌ Could not find file: {csv_path}")
                except Exception as e:
                    print(f"      ❌ Error restoring '{table}': {e}")

            conn.commit()

        print(
            "\n🎉 RESTORE COMPLETE! Your app should be fully functional with all old data."
        )

    except Exception as e:
        print(f"\n❌ Connection Error: {e}")


if __name__ == "__main__":
    restore()
