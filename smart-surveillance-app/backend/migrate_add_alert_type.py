#!/usr/bin/env python3
"""
Migration script to add alert_type column to alerts table.
Run this script to update the database schema.
"""

import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_root))

from backend.database.session import engine
from sqlalchemy import text

def run_migration():
    """Add alert_type column to alerts table."""
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'alerts' AND column_name = 'alert_type'
            """))

            if result.fetchone():
                print("Column 'alert_type' already exists in alerts table")
                return

            # Add the column
            print("Adding 'alert_type' column to alerts table...")
            conn.execute(text("""
                ALTER TABLE alerts
                ADD COLUMN alert_type VARCHAR(50) DEFAULT 'zone'
            """))
            conn.commit()
            print("Successfully added 'alert_type' column to alerts table")

    except Exception as e:
        print(f"Error running migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migration()