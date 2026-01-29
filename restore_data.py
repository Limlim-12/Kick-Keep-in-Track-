import pandas as pd
from sqlalchemy import create_engine, text
import os

# Uses the URL you just set in the terminal
NEW_DB_URL = os.environ.get("DATABASE_URL")
BACKUP_FOLDER = "rescue_backup"


def restore():
    if not NEW_DB_URL:
        print("❌ Error: DATABASE_URL is not set.")
        print("   Run: $env:DATABASE_URL = '...' first.")
        return

    print(f"🚀 Restoring to: {NEW_DB_URL.split('@')[-1]}...")

    try:
        engine = create_engine(NEW_DB_URL)

        # 1. TABLES ORDER (Parents first)
        tables = [
            "regions",
            "users",
            "clients",
            "tickets",
            "activity_logs",
            "email_logs",
            "ticket_attachments",
            "announcements",
        ]

        with engine.connect() as conn:
            for table in tables:
                file_path = f"{BACKUP_FOLDER}/{table}.csv"
                if os.path.exists(file_path):
                    print(f"   Processing '{table}'...")
                    try:
                        df = pd.read_csv(file_path)
                        if not df.empty:
                            # Upload data
                            df.to_sql(table, conn, if_exists="append", index=False)
                            print(f"      ✅ Restored {len(df)} rows.")

                            # Reset ID counters so new data doesn't crash
                            if "id" in df.columns:
                                max_id = df["id"].max()
                                if pd.notna(max_id):
                                    seq_name = f"{table}_id_seq"
                                    conn.execute(
                                        text(
                                            f"SELECT setval('{seq_name}', {int(max_id)})"
                                        )
                                    )
                                    print(f"      🔧 Fixed ID counter.")
                    except Exception as e:
                        print(f"      ❌ Error uploading {table}: {e}")
                else:
                    print(f"   ⚠️  File {table}.csv not found. Skipping.")

            conn.commit()
        print("\n🎉 RECOVERY COMPLETE! kick-db-v4 is live.")

    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        print("Tip: Check if your IP is allowed or if the URL is correct.")


if __name__ == "__main__":
    restore()
