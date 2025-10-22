from kick_app import create_app, db
from kick_app.models import User, Region  # This import is already here

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """
    Makes variables available in the 'flask shell' for easy testing.
    """
    return {"db": db, "User": User, "Region": Region}


# --- ADD THIS NEW CODE BLOCK ---
@app.cli.command("seed-db")
def seed_db_command():
    """Creates the initial data for the app (e.g., regions)."""

    # Check if regions already exist
    if Region.query.filter_by(name="Metro").first():
        print("Regions already exist. Skipping seed.")
        return

    # Create the region data
    r1 = Region(name="Metro")
    r2 = Region(name="North")
    r3 = Region(name="South")

    db.session.add_all([r1, r2, r3])
    db.session.commit()

    print("Successfully seeded the database with regions.")


# --- END OF NEW CODE ---


if __name__ == "__main__":
    app.run(debug=True)
