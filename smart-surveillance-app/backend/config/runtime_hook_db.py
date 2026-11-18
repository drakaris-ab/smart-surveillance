"""
Runtime hook to ensure surveillance.db is in the correct location when running as a frozen executable.
When running from PyInstaller, the database ends up in _internal/ but the code looks for it next to the exe.
This hook copies it on first run.
"""
import os
import sys
import shutil

def ensure_database_location():
    if getattr(sys, "frozen", False):
        # Running as PyInstaller executable
        exe_dir = os.path.dirname(sys.executable)
        db_name = "surveillance.db"

        # Target location: next to the executable
        target_db = os.path.join(exe_dir, db_name)

        # Source location: in _internal folder
        internal_dir = os.path.join(os.path.dirname(sys.executable), "_internal")
        source_db = os.path.join(internal_dir, db_name)

        # If database doesn't exist at target but exists in _internal, copy it
        if not os.path.exists(target_db) and os.path.exists(source_db):
            try:
                shutil.copy2(source_db, target_db)
                print(f"[Runtime Hook] Copied {db_name} from _internal to exe directory")
            except Exception as e:
                print(f"[Runtime Hook] Failed to copy database: {e}")

# Run immediately
ensure_database_location()