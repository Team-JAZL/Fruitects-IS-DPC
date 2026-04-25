import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
from fastapi import FastAPI
import sqlite3
import time
from database import init_db, update_job_status

app = FastAPI()
init_db()

@app.post("/publish")
async def publish(data: dict):
    conn = sqlite3.connect('fruit_system.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Jobs (message_id, topic, image_base64, status) 
        VALUES (?, ?, ?, ?)
    """, (data['message_id'], data['topic'], data['image_data'], 'PENDING'))
    conn.commit()
    conn.close()
    print(f"New job queued: {data['message_id']} for {data['topic']}")
    return {"status": "queued"}

@app.get("/subscribe/fruit/{fruit_type}")
async def subscribe(fruit_type: str):
    topic = f"fruit/{fruit_type.lower()}"
    conn = sqlite3.connect('fruit_system.db')
    cursor = conn.cursor()
    
    # Lease & Retry logic
    timeout_limit = time.time() - 60
    cursor.execute("""
        SELECT * FROM Jobs 
        WHERE topic=? AND (status='PENDING' OR (status='IN_PROGRESS' AND lease_timestamp < ?))
        ORDER BY rowid DESC LIMIT 1
    """, (topic, timeout_limit))
    
    job = cursor.fetchone()
    conn.close()
    
    if job:
        # Update status to IN_PROGRESS agad para hindi na makuha ng iba
        update_job_status(job[0], 'IN_PROGRESS')
        print(f"📦 Job {job[0]} leased to {fruit_type} worker")
        return {
            "message_id": job[0], 
            "image_data": job[2], 
            "topic": job[1]
        }
    return {"status": "no_jobs"}

@app.post("/ack")
async def acknowledge(data: dict):
    print(f"Received ACK for job: {data['message_id']}")
    update_job_status(data['message_id'], 'COMPLETED', data['result'])
    return {"status": "confirmed"}


@app.get("/history")
async def get_history():
    conn = sqlite3.connect('fruit_system.db')
    cursor = conn.cursor()
    # We will fetch only completed jobs and parse the result_payload to return a more readable history
    cursor.execute("SELECT message_id, topic, result_payload FROM Jobs WHERE status='COMPLETED' ORDER BY lease_timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        # Parse the result_payload JSON string back to a dictionary
        result = json.loads(row[2]) if row[2] else {}
        history.append({
            "job_id": row[0],
            "fruit": row[1].split('/')[-1].capitalize(),
            "disease": result.get("disease", "Unknown"),
            "confidence": result.get("confidence", "0%")
        })
    return history