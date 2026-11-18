import sys
import os
import sqlite3

# Drop the table directly using sqlite3
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'surveillance.db')
print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("DROP TABLE IF EXISTS alert_mute_schedules;")
    conn.commit()
    print("Table 'alert_mute_schedules' dropped successfully.")
except Exception as e:
    print(f"Error dropping table: {e}")
finally:
    conn.close()

# Recreate the tables using SQLAlchemy
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.database.session import engine
from backend.database.models import Base
Base.metadata.create_all(bind=engine)
print("Tables recreated with new schema.")
