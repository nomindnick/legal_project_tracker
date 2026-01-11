#!/usr/bin/env python3
"""Database reset script for Legal Project Tracker.

Clears all projects from the database and re-seeds with fake data.
Useful for resetting to a known state during development and testing.

Usage:
    python scripts/reset_db.py

WARNING: This will delete ALL existing project data!
"""
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import Project
from scripts.seed_data import seed_database


def main():
    """Main entry point for reset script."""
    app = create_app()

    with app.app_context():
        # Count existing projects
        existing_count = db.session.query(Project).count()
        print(f"Current database has {existing_count} projects.")

        # Confirm reset
        if existing_count > 0:
            response = input("This will delete all projects. Continue? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted.")
                return

        # Delete all projects (hard delete for reset purposes)
        print("Deleting all projects...")
        db.session.query(Project).delete()
        db.session.commit()
        print("All projects deleted.")

        # Re-seed
        print("\nSeeding database with fake projects...")
        count = seed_database()
        print(f"Created {count} projects.")

        print("\nReset complete!")


if __name__ == "__main__":
    main()
