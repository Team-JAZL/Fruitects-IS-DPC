import os
import sqlite3
import time
import json

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'fruit_system.db'))



def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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


# helper functions

def insert_job(message_id, topic, image_base64):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try: 
        cursor.execute("""
            INSERT INTO Jobs (message_id, topic, image_base64, status)
            VALUES (?,?,?,?)
        """, (message_id, topic, image_base64, 'PENDING'))
        conn.commit()
    except Exception as e:
        print(f"DB ERROR inserting job: {e}")
    finally: 
        conn.close()

def fetch_and_lease_job(topic, timeout_limit):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    job_data = None

    try: 
        cursor.execute(
            """ SELECT message_id, topic, image_base64 FROM Jobs
                WHERE topic = ? AND (status = 'PENDING' OR (status = 'IN_PROGRESS' AND lease_timestamp <?))
                ORDER BY rowid ASC LIMIT 1
            """, (topic, timeout_limit))
        row = cursor.fetchone()
        
        if row:
            job_data = {
                "message_id": row[0],
                "topic": row[1],
                "image_data": row[2]
            }
    except Exception as e: 
        print(f"DB Error fetching job: {e}")
    finally: 
        conn.close()
    return job_data


def get_completed_jobs():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    history = []

    try: 
        cursor.execute("SELECT message_id, topic, image_base64, result_payload, lease_timestamp FROM Jobs WHERE status='COMPLETED' ORDER BY lease_timestamp ASC")
        rows = cursor.fetchall()
        fruit_counts = {}
        for row in rows:
            fruit = row[1].split('/')[-1].capitalize()
            fruit_counts[fruit] = fruit_counts.get(fruit, 0) + 1
            result = json.loads(row[3]) if row[3] else {}
            analyzed_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row[4])) if row[4] else None
            history.append({
                "job_id": row[0],
                "fruit": fruit,
                "fruit_id": f"{fruit}_{fruit_counts[fruit]}",
                "disease": result.get("disease", "Unknown"),
                "confidence": result.get("confidence", "0%"),
                "analyzed_at": analyzed_at,
                "image_data": row[2]
            })
    except Exception as e:
        print(f"DB Error fetching history: {e}")
    finally: 
        conn.close()
    return history


def get_queue_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    queue = []

    try:
        cursor.execute(
            "SELECT rowid, message_id, topic, image_base64, status FROM Jobs WHERE status IN ('PENDING', 'IN_PROGRESS', 'PROCESSING') ORDER BY rowid ASC"
        )
        rows = cursor.fetchall()
        for row in rows:
            queue.append({
                "position": row[0],
                "message_id": row[1],
                "topic": row[2],
                "image_base64": row[3],
                "status": row[4]
            })
    except Exception as e:
        print(f"DB Error fetching queue: {e}")
    finally:
        conn.close()

    return queue


def clear_queue_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Jobs WHERE status IN ('PENDING', 'IN_PROGRESS', 'PROCESSING')")
        conn.commit()
    except Exception as e:
        print(f"DB Error clearing queue: {e}")
    finally:
        conn.close()


def delete_completed_job(message_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Jobs WHERE message_id = ? AND status = 'COMPLETED'", (message_id,))
        conn.commit()
    except Exception as e:
        print(f"DB Error deleting completed job: {e}")
    finally:
        conn.close()

    vacuum_db()


def clear_completed_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Jobs WHERE status = 'COMPLETED'")
        conn.commit()
    except Exception as e:
        print(f"DB Error clearing completed jobs: {e}")
    finally:
        conn.close()

    vacuum_db()


def vacuum_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('VACUUM')
        conn.commit()
    except Exception as e:
        print(f"DB Error vacuuming database: {e}")
    finally:
        conn.close()
