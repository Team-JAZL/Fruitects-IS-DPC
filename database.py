import sqlite3
import time
import json

def init_db():
    conn = sqlite3.connect('fruit_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Jobs (
            message_id TEXT PRIMARY KEY,
            topic TEXT,
            image_base64 TEXT,
            status TEXT,
            lease_timestamp REAL,
            result_payload TEXT
        )
    ''')
    conn.commit()
    conn.close()

def update_job_status(message_id, status, result=None):
    conn = sqlite3.connect('fruit_system.db')
    cursor = conn.cursor()
    try:
        if status == 'COMPLETED' and result is not None:
            # Finalize and save AI results
            cursor.execute("""
                UPDATE Jobs 
                SET status = ?, result_payload = ?, lease_timestamp = ? 
                WHERE message_id = ?
            """, (status, json.dumps(result), time.time(), message_id))
        else:
            # Set to IN_PROGRESS
            cursor.execute("""
                UPDATE Jobs 
                SET status = ?, lease_timestamp = ? 
                WHERE message_id = ?
            """, (status, time.time(), message_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()